#copyright all rights reserved Lawrence Arnstein 2019
#other components, connectivity, undo/redo, pressure modeling, impellers, etc.
#todo: bug label interferes with handle on rotated Tap, Undo cross over load new model!!,
#todo: timer for handles, springs,name ports, abstract, select conflict with menu...disable mouse effects when in menu
#todo: move undo/redo stack into module. Add visbility control to Module. Load all modules at all times in project
#todo: corner case: disconnecting a pump from an output causes pressure to change on update not on pressure equalize. So the abstract is wrong until moved. need away to push this back to module
import os, sys
import pygame
import pygame.gfxdraw
import pygame_gui as pg
from operator import sub
from operator import add
import traceback
import json

from pygame.locals import *

if not pygame.font: print('Warning, fonts disabled')
if not pygame.mixer: print('Warning, sound disabled')

guage = 20
segment = 60
OUT = False
IN = True
downPos = None
lastPos = None
currentHandle = None
currentImpeller = None
currentModule = None
loaded_modules = {}

pygame.init()
screen_w = 1200
screen_h = 700
ui_width = 160
ui_height = 20
ui_space = 30
pauseEqualize = False
screen = pygame.display.set_mode((screen_w, screen_h))
pygame.display.set_caption('tcPlumbing')
pygame.mouse.set_visible(1)

manager = pg.UIManager((1200, 700))
new_button = pg.elements.UIButton(relative_rect=pygame.Rect((screen_w-ui_width-10,10), (ui_width, ui_height)),
                                            text='New',
                                            manager=manager)
module_name = pg.elements.UITextEntryLine(relative_rect=pygame.Rect((10,10), (ui_width, ui_height)),
                                            manager=manager)
speed_slider = pg.elements.UIHorizontalSlider(relative_rect=pygame.Rect((screen_w-ui_width-10,10+ui_space),(ui_width, ui_height)),value_range=tuple((0.05,1.0)),manager=manager,start_value=0.9)
commands = ["duplicate      d","rotate         r","flip           f","copy           c","paste          v","grow           g","shrink         s","undo           z","redo           y","no handles      q"]
command_list = pg.elements.UIDropDownMenu(options_list=commands, starting_option = "Commands", manager=manager,relative_rect=pygame.Rect((screen_w-ui_width-10,130),(ui_width, ui_height)))

gui_elements = []
gui_elements.append(module_name)
gui_elements.append(command_list)
gui_elements.append(new_button)
gui_elements.append(speed_slider)

if not os.path.exists('projects'):
    os.makedirs('projects')

def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)
    image = image.convert_alpha()
    return image, image.get_rect()

class Module(pygame.sprite.Sprite) :
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.pipes = pygame.sprite.RenderPlain()
        self.ports = pygame.sprite.RenderPlain()
        self.handles = pygame.sprite.RenderPlain()
        self.instances = pygame.sprite.RenderPlain()
        self.changeQueue = []
        self.connections = []
        self.impellers = pygame.sprite.RenderPlain()
        self.labels = pygame.sprite.RenderPlain()
        self.changed = False
        self.visible = True
        self.module = None
        self.handle = None
        self.selected = False
        self._x = None
        self._y = None
        self.suppress_undoable = False
        self.initUndoStack()
        self.updateAbstractNow = False
        self.upateAbstract = False
        self.buildAbstract()

    def getInstance(self):
        instance = Module()
        instance.loadSerializationMap(self.getSerializationMap())
        instance.changed = True
        instance.module = self
        instance._x = screen_w/2
        instance._y = screen_h/2
        instance.buildAbstract()
        instance.handle = Handle(instance)
        currentModule.addHandle(instance.handle)
        currentModule.instances.add(instance)
        instance.update()
        return instance

    def move(self, delta, handle):
        global lastPos
        if self.module :
            dx = round(delta[0]/halfGuage) * halfGuage
            dy = round(delta[1]/halfGuage) * halfGuage
            self._x = self._x + dx
            self._y = self._y + dy
            if handle == currentHandle : #compensate for snapping to grid so that errors don't accumulate
                ex = dx - delta[0]
                ey = dy - delta[1]
                lastPos = (lastPos[0]+ex+delta[0], lastPos[1] + ey+delta[1])
            self.changed = True
            self.rect.center = (self._x,self._y)

    def initUndoStack(self):
        if not self.suppress_undoable :
            self.undo_stack = [json.dumps(self.getSerializationMap())]
            self.undo_ix = 0
            self.suppress_undoable = False

    def addQueue(self, connection) :
        if connection not in self.changeQueue :
            self.changeQueue.append(connection)

    def addPipe(self, p):
        self.pipes.add(p)
        self.changed = True

    def addImpeller(self, imp):
        self.impellers.add(imp)
        self.changed = True

    def addLabel(self, l) :
        self.labels.add(l)
        self.changed = True

    def removePipe(self,p):
        self.pipes.remove(p)
        self.handles.remove(p.handle)
        self.ports.remove(p.inPort)
        self.ports.remove(p.outPort)
        self.ports.remove(p.ctlPort)
        self.impellers.remove(p.impeller)
        self.labels.remove(p.label)
        self.changed = True

    def addHandle(self, h):
        self.handles.add(h)
        self.changed = True

    def addPort(self,p):
        self.ports.add(p)
        self.changed = True

    def addConnection(self,c) :
        self.connections.append(c)

    def removeConnection(self,c):
        c.close()
        self.connections.remove(c)
        self.changeQueue.remove(c)

    def getSerializationMap(self):
        datastore = {}
        datastore["components"] = []
#        datastore["connections"] = []
        for p in self.pipes :
            datastore["components"].append(p.getSerializationMap())
#        for c in self.connections :
#            datastore["connections"].append(c.getSerializationMap())
        return datastore

    def loadComponent(self, c, offsetx, offsety):
        class_ = classes[c["type"]]
        p = class_(self, offsetx,offsety)
        p.loadSerializationMap(c, True)
        return p

    def loadSerializationMap(self, datastore):
        self.pipes = pygame.sprite.RenderPlain()
        self.ports = pygame.sprite.RenderPlain()
        self.handles = pygame.sprite.RenderPlain()
        self.impellers = pygame.sprite.RenderPlain()
        self.labels = pygame.sprite.RenderPlain()
        self.changeQueue = []
        self.connections = []
        self.initUndoStack()
        components = datastore["components"]
        for c in components :
            self.loadComponent(c,0,0)
        self.changed = True

    def undo(self):
        if len(self.undo_stack) >= self.undo_ix and self.undo_ix > 0:
            self.undo_ix -= 1
            serialized_module = self.undo_stack[self.undo_ix]
            self.suppress_undoable = True
            self.loadSerializationMap(json.loads(serialized_module))

    def redo(self):
        if self.undo_ix  < len(self.undo_stack) - 1 :
            self.undo_ix += 1
            serialized_module = self.undo_stack[self.undo_ix]
            self.suppress_undoable = True
            self.loadSerializationMap(json.loads(serialized_module))

    def update(self):
        for p in self.pipes:
            if p.changed:
                p.update()
                if p.io is not None : self.updateAbstract = True
        for instance in self.instances :
            instance.update()
        if self.changed :
            self.updateAbstract = True
            pressed1, pressed2, pressed3 = pygame.mouse.get_pressed()
            if pressed1 or pressed2 or pressed3: return

            if not self.suppress_undoable :
                old_module = json.dumps(self.getSerializationMap())
                self.undo_ix += 1
                if len(self.undo_stack) > 0:
                    del self.undo_stack[self.undo_ix:]
                self.undo_stack.append(old_module)
                self.undo_ix = len(self.undo_stack) - 1

            self.suppress_undoable = False

            for c in self.connections :
                c.close()
            self.connections = []
            for p in self.ports :
                for q in self.ports :
                    if p.connected is None and not q.connected and p.pipe.id < q.pipe.id and p.orientation() == q.orientation() and p.direction^q.direction and p.rect.colliderect(q.rect) :
                        self.addConnection(Connection(p,q))
                        p.pipe.changed = True
                        q.pipe.changed = True
            self.changed = False
            self.updateAbstract = True
            self.changeQueue = self.connections.copy()
            self.save()

        if not pauseEqualize :
            oldQ = self.changeQueue.copy()
            self.changeQueue = []
            for c in oldQ :
                c.equalize()
            if (self.updateAbstract and len(self.changeQueue) == 0) or self.updateAbstractNow :
                self.buildAbstract()
                self.updateAbstractNow = False

    def buildAbstract(self):
        # construct sprite for the module abstract
        input_pipes = []
        output_pipes = []
        for p in self.pipes:
            if p.io is not None:
                if p.io == IN : input_pipes.append(p)
                elif p.io == OUT : output_pipes.append(p)
        input_pipes.sort(key=lambda portname: portname.name)
        output_pipes.sort(key=lambda portname: portname.name)
        boxw = 160
        width = (segment / 2) * 2 + boxw
        maxports = max(len(input_pipes), len(output_pipes))
        height = (guage * maxports) + halfGuage * (maxports + 1)
        abstract = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.gfxdraw.rectangle(abstract, (0, 0, width, height), (180, 180, 180))
        pygame.gfxdraw.box(abstract, (segment / 2, 0, boxw, height), (180, 180, 180))
        name = module_name.text
        if self.module : name = "instance"
        nameSurf = pygame.font.SysFont("Arial", 14).render(name, True, pygame.Color(255, 255, 255), None)
        abstract.blit(nameSurf,
                      (width / 2 - nameSurf.get_rect().width / 2, (height / 2 - nameSurf.get_rect().height / 2)-guage))
        starty = halfGuage-qtrGuage
        for i in input_pipes:
            img = full_pipe_img.copy()
            img.fill(scalarToColor(i.outPressure), special_flags=pygame.BLEND_MULT)
            abstract.blit(img, (0, starty), pygame.Rect(0, 40, segment / 2, 2 * guage))
            nameSurf = pygame.font.SysFont("Arial", 12).render(i.name, True, pygame.Color(255, 255, 255), None)
            abstract.blit(nameSurf, (segment / 2, starty))
            starty += (guage + halfGuage)
        starty = halfGuage-qtrGuage
        for i in output_pipes:
            img = full_pipe_img.copy()
            img.fill(scalarToColor(i.inPressure), special_flags=pygame.BLEND_MULT)
            abstract.blit(img, (segment / 2 + boxw, starty), pygame.Rect(0, 40, segment / 2, 2 * guage))
            nameSurf = pygame.font.SysFont("Arial", 12).render(i.name, True, pygame.Color(255, 255, 255), None)
            abstract.blit(nameSurf, (segment / 2 + boxw - nameSurf.get_rect().width, starty))
            starty += (guage + halfGuage)
        self.image = abstract
        self.rect = abstract.get_bounding_rect()
        if self.module :
            self.rect.center = (self._x,self._y)
        else :
            self.rect.center = ((screen_w - width / 2) - 20, (screen_h - height / 2) - 20)
        self.updateAbstract = False

    def save(self):
        serialized_module = self.getSerializationMap()
        if module_name.text != "":
            file = os.path.join("projects", module_name.text + ".json")
            with open(file, 'w') as f:
                json.dump(serialized_module, f)
                f.close()


halfGuage = int(guage/2)
qtrGuage = int(guage/4)

#handle representations
selectedHandle = pygame.Surface((halfGuage+1, halfGuage+1), pygame.SRCALPHA)
pygame.gfxdraw.filled_circle(selectedHandle, qtrGuage, qtrGuage, qtrGuage, (220, 0, 0))

overHandle = pygame.Surface((halfGuage+1, halfGuage+1), pygame.SRCALPHA)
pygame.gfxdraw.filled_circle(overHandle, qtrGuage, qtrGuage, qtrGuage, (128, 128, 128))
pygame.gfxdraw.aacircle(overHandle, qtrGuage, qtrGuage, qtrGuage, (128, 128, 128))

ghostHandle = pygame.Surface((halfGuage+1, halfGuage+1), pygame.SRCALPHA)
pygame.gfxdraw.aacircle(ghostHandle, qtrGuage, qtrGuage, qtrGuage, (128, 128, 128))

#port representations
disconnectedInPort = pygame.Surface((halfGuage+1,halfGuage+1), pygame.SRCALPHA)
pygame.gfxdraw.filled_trigon(disconnectedInPort,0,0,0,halfGuage,halfGuage,int(halfGuage/2),pygame.Color(0,220,0))

ghostInPort = pygame.Surface((halfGuage+1,halfGuage+1), pygame.SRCALPHA)
pygame.gfxdraw.aatrigon(ghostInPort,0,0,0,halfGuage,halfGuage,int(halfGuage/2),pygame.Color(128,128,128))

disconnectedOutPort = pygame.Surface((halfGuage+1,halfGuage+1), pygame.SRCALPHA)
pygame.gfxdraw.filled_trigon(disconnectedOutPort,0,0,0,halfGuage,halfGuage,int(halfGuage/2),pygame.Color(0,0,220))

ghostOutPort = pygame.Surface((halfGuage+1,halfGuage+1), pygame.SRCALPHA)
pygame.gfxdraw.aatrigon(ghostOutPort,0,0,0,halfGuage,halfGuage,int(halfGuage/2),pygame.Color(128,128,128))

invisibleDecoration = pygame.Surface((halfGuage+1,halfGuage+1), pygame.SRCALPHA)

MAXPRESSURE = 255
MAXFLOW = 0.5
def scalarToColor(p) :
  s = p/MAXPRESSURE
  c2 = pygame.Color(255 - int(s*(255-127)), 255 - int(s*(255-205)), 255 - int(s*(255-255)));
  return c2

def equalizePressure(inputPressure,currentPressure,aperture) :
    deltap =  aperture * speed_slider.get_current_value() * (inputPressure - currentPressure)
    newp = round(100.0 * (currentPressure + deltap)) / 100.0
    if deltap > 0 and newp > (0.9 * MAXPRESSURE): newp = MAXPRESSURE
    if deltap < 0 and newp < (0.1 * MAXPRESSURE): newp = 0
    return newp

class Label(pygame.sprite.Sprite) :
    def __init__(self, pipe):
        pygame.sprite.Sprite.__init__(self)
        self.pipe = pipe
        pipe.module.addLabel(self)
        self.mirror = 1

    def update(self, *args) :
        center = tuple(map(add, self.pipe.rect.center, (0, -guage)))
        if self.pipe.angle == 1 :
            center = tuple(map(add, self.pipe.rect.center, (0, self.mirror * -guage)))
        if self.pipe.angle == 2 :
            center = tuple(map(add, self.pipe.rect.center, (0, guage)))
        if self.pipe.angle == 3 :
            center = tuple(map(add, self.pipe.rect.center, (0, self.mirror * guage)))

        font = pygame.font.SysFont("Arial", 14)
        textSurf = font.render(self.pipe.name, True, pygame.Color(255,255,255), None)
        self.image = pygame.Surface((160, 20), pygame.SRCALPHA)
        self.image.blit(textSurf, [0,0])
        self.rect = self.image.get_bounding_rect()
        self.rect.center = center

MAXRATE = 30
class Impeller(pygame.sprite.Sprite) :
    def __init__(self, pipe):
        pygame.sprite.Sprite.__init__(self)
        self.pipe = pipe
        pipe.module.addImpeller(self)
        self.angle = 0
        self.image = pygame.transform.rotate(impeller_img, self.angle)
        self.rect = self.image.get_rect()

    def update(self, *args) :
        center = tuple(map(add, self.pipe.rect.center, (0, guage)))
        if self.pipe.angle == 1 :
            center = tuple(map(add, self.pipe.rect.center, (-guage, 0)))
        if self.pipe.angle == 2 :
            center = tuple(map(add, self.pipe.rect.center, (0, -guage)))
        if self.pipe.angle == 3 :
            center = tuple(map(add, self.pipe.rect.center, (guage, 0)))
        rotated_image = pygame.transform.rotate(impeller_img,self.angle)
        rate = MAXRATE * self.pipe.outPressure/255
        green = int(rate/MAXRATE * 255)
        rotated_image.fill(pygame.Color(255-green,255,255-green), special_flags=pygame.BLEND_MULT)
        new_rect = rotated_image.get_rect(center=center)
        self.image = rotated_image
        self.rect = new_rect
        self.angle = (self.angle + rate) % 360

    def switch(self):
        if isinstance(self.pipe, Tap) :
            self.pipe.switch()

class Connection() :
    def __init__(self, a, b):
        if a.direction == OUT :
            self.src = a
            self.sink = b
        else :
            self.src = b
            self.sink = a
        self.src.connected = self
        self.sink.connected = self

    def equalize(self):
        src = self.src.pipe.getPortPressure(self.src)
        sink = self.sink.pipe.getPortPressure(self.sink)
        newp2 = equalizePressure(src,sink,1.0)
        if src != newp2 :
            self.sink.pipe.module.addQueue(self)
        self.sink.pipe.updatePressure(newp2,self.sink)

    def close(self):
        self.src.connected = None
        self.sink.connected = None
        self.src.pipe.changed = True
        self.sink.pipe.changed = True

    def getSerializationMap(self):
        serialDict = {}
        return serialDict

class Port(pygame.sprite.Sprite) :
    def __init__(self, p):
        pygame.sprite.Sprite.__init__(self)
        self.pipe = p
        self.connected = None
        self.alignedWithPipe = True
        self.direction = None
        self.id = None

    def rotate(self):
        center = self.rect.center
        rotated_image = pygame.transform.rotate(self.image,-90)
        new_rect = rotated_image.get_rect(center = center)
        self.image = rotated_image
        self.rect = new_rect

    def orientation(self) :
       if self.alignedWithPipe : return self.pipe.orientation
       return not self.pipe.orientation

class InPort(Port) :
    # Constructor. Pass in the color of the block,
    # and its x and y position
    def __init__(self, p):
        Port.__init__(self,p)
        self.id = 0
        self.direction = IN

    def constructImage(self):
        global decorationsVisible
        if self.connected is None :
            self.image = disconnectedInPort
        elif decorationsVisible :
            self.image = ghostInPort
        else :
            self.image = invisibleDecoration
        self.rect = self.image.get_bounding_rect()
        self.rect.center = self.pipe.rect.center

class CtlPort(InPort) :
    def __init__(self, p):
        InPort.__init__(self,p)

class OutPort(Port) :
    # Constructor. Pass in the color of the block,
    # and its x and y position
    def __init__(self, p):
        Port.__init__(self, p)
        self.id = 1
        self.direction = OUT

    def constructImage(self):
        if self.connected is None:
            self.image = disconnectedOutPort
        elif decorationsVisible :
            self.image = ghostOutPort
        else :
            self.image = invisibleDecoration
        self.rect = self.image.get_bounding_rect()
        self.rect.center = self.pipe.rect.center

#Handle
class Handle(pygame.sprite.Sprite):
    def __init__(self, component) :
        pygame.sprite.Sprite.__init__(self)
        self.component = component
        self.image = ghostHandle
        self.rect = self.image.get_bounding_rect()
        self.rect.center = self.component.rect.center
        self.name = ""

    def move(self,delta):
        self.component.move(delta,self)

    def select(self,s):
        self.component.selected = s
        if s: self.image = selectedHandle

    def toggleSelected(self):
        self.select(not self.pipe.selected)

    def applyOverHandle(self):
        self.image = overHandle

    def applyGhostHandle(self):
        if decorationsVisible :
            self.image = ghostHandle
        else :
            self.image = invisibleDecoration

    def applySelectedHandle(self):
        self.image = selectedHandle

    def update(self, *args):
        self.rect.center = (self.component._x, self.component._y)

nextID = 0
decorationsVisible = True

class Pipe(pygame.sprite.Sprite):
    def __init__(self,m,x,y) : # call Sprite intializer
        global nextID
        pygame.sprite.Sprite.__init__(self)
        self.id = nextID
        nextID = nextID + 1
        self.image = pygame.Surface((60, 100), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.module = m
        m.addPipe(self)
        self._x = round(x/halfGuage) * halfGuage
        self._y = round(y/halfGuage) * halfGuage
        self.angle = 0
        self.selected = False
        self.orientation = True
        self.mirror = 1
        self.sfactor = 0
        self.handle = Handle(self)
        self.inPort = InPort(self)
        self.outPort = OutPort(self)
        self.ctlPort = None
        self.changed = True
        self.inPressure = self.outPressure = 0
        self.impeller = None
        self.label = None
        self.io = None
        self.name = ""
        m.addHandle(self.handle)
        m.addPort(self.inPort)
        m.addPort(self.outPort)

    def turnOffDecorations(self):
        if self.inPort : self.inPort.image = invisibleDecoration
        if self.outPort : self.outPort.image = invisibleDecoration
        if self.ctlPort : self.ctlPort.image = invisibleDecoration
        if not self.selected : self.handle.image = invisibleDecoration

    def turnOnDecorations(self):
        self.constructImage()

    def setName(self, name):
        if name != "" : self.name = name

    def getPortPressure(self, p):
        if p == self.inPort : return self.inPressure
        if p == self.outPort : return self.outPressure
        return None

    def transferPressure(self):
        p = self.outPressure
        if self.inPort.connected is None:
            if self.inPressure : self.pressureChanged(IN)
            self.inPressure = 0
        self.outPressure = self.inPressure
        if p != self.outPressure :
            self.pressureChanged(OUT)

    def pressureChanged(self,d):
        self.changed = True
        if d == OUT :
            if self.outPort is not None and self.outPort.connected is not None and self.outPort.direction == OUT :
                self.module.addQueue(self.outPort.connected)
            if self.ctlPort is not None and self.ctlPort.connected is not None and self.ctlPort.direction == OUT:
                self.module.addQueue(self.ctlPort.connected)

    def constructPortImages(self):
        if self.inPort : self.inPort.constructImage()
        if self.outPort : self.outPort.constructImage()

    def updatePressure(self,p,src):
        oldp = self.inPressure
        if src == self.inPort :
            self.inPressure = p
        if oldp != self.inPressure :
            self.changed = True
            self.transferPressure()

    def addSprites(self):
        if not self.module.module :
            img = pipe_img.copy()
            img.fill(scalarToColor(self.outPressure), special_flags=pygame.BLEND_MULT)
            self.image.blit(img,(0,0))
            img = pipe_img.copy()
            img.fill(scalarToColor(self.inPressure), special_flags=pygame.BLEND_MULT)
            self.image.blit(img,(-segment/2,0))

    def constructImage(self):
        global pipe_img, pipe_rect
        self.image = pygame.Surface((60, 100), pygame.SRCALPHA)
        self.addSprites()
        self.rect = self.image.get_rect()
        self.rect.center = self._x, self._y
        self.constructPortImages()
        self.rescale()
        self.reflip()
        for i in range(self.angle) : self.rerotate()
        self.changed = False

    def update(self, *args):
        pygame.sprite.Sprite.update(self)
        self.transferPressure()
        self.handle.update(self)
        if self.inPort : self.inPort.update(self)
        if self.outPort: self.outPort.update(self)
        if self.changed : self.constructImage()

    def rotate(self):
        self.angle = divmod(self.angle+1, 4)[1]
        self.orientation = not self.orientation
        self.changed = True
        self.module.changed = True

    def rerotate(self) :
        center = (self._x, self._y)
        rotated_image = pygame.transform.rotate(self.image,-90)
        new_rect = rotated_image.get_rect(center=center)
        self.image = rotated_image
        self.rect = new_rect
        if self.inPort : self.inPort.rotate()
        if self.outPort : self.outPort.rotate()

    def scale(self,s):
        self.sfactor = max(-2,self.sfactor+s)
        self.module.changed = True
        self.changed = True

    def rescale(self) :
        center = (self._x, self._y)
        sy = self.image.get_height()
        sx = round(((segment+self.sfactor*guage)/segment) * segment)
        scaled_image = pygame.transform.scale(self.image, (sx,sy))
        new_rect = scaled_image.get_rect(center=center)
        self.image = scaled_image
        self.rect = new_rect
        if self.angle == 0 :
            if self.inPort : self.inPort.rect.center = tuple(map(add,self.rect.center,(-sx/2 + qtrGuage,0)))
            if self.outPort : self.outPort.rect.center = tuple(map(add,self.rect.center,(sx/2 - qtrGuage,0)))
        elif self.angle == 1 :
            if self.inPort : self.inPort.rect.center = tuple(map(add,self.rect.center,(0,-sx/2 + qtrGuage)))
            if self.outPort :self.outPort.rect.center = tuple(map(add,self.rect.center,(0,sx/2 - qtrGuage)))
        elif self.angle == 2 :
            if self.inPort : self.inPort.rect.center = tuple(map(add,self.rect.center,(sx/2 - qtrGuage,0)))
            if self.outPort :self.outPort.rect.center = tuple(map(add,self.rect.center,(-sx/2 + qtrGuage,0)))
        else :
            if self.inPort : self.inPort.rect.center = tuple(map(add,self.rect.center,(0,sx/2 - qtrGuage)))
            if self.outPort :self.outPort.rect.center = tuple(map(add,self.rect.center,(0,-sx/2 + qtrGuage)))

    def flip(self):
        self.mirror = -1 * self.mirror
        self.module.changed = True
        self.changed = True

    def reflip(self) :
        if self.mirror == -1 :
            center = (self._x, self._y)
            flipped_image = pygame.transform.flip(self.image,False,True)
            new_rect = flipped_image.get_rect(center=center)
            self.image = flipped_image
            self.rect = new_rect

    def move(self, delta, handle):
        global lastPos
        dx = round(delta[0]/halfGuage) * halfGuage
        dy = round(delta[1]/halfGuage) * halfGuage
        self._x = self._x + dx
        self._y = self._y + dy
        if handle == currentHandle : #compensate for snapping to grid so that errors don't accumulate
            ex = dx - delta[0]
            ey = dy - delta[1]
            lastPos = (lastPos[0]+ex+delta[0], lastPos[1] + ey+delta[1])
        self.module.changed = True
        self.changed = True

    def getSerializationMap(self):
        m = {}
        m["type"] = self.__class__.__name__
        m["x"] = self._x
        m["y"] = self._y
        m["angle"] = self.angle
        m["flip"] = self.mirror
        m["scale"] = self.sfactor
        m["orientation"] = self.orientation
        m["id"] = self.id
        m["name"] = self.name
        return m

    def loadSerializationMap(self,m,new) :
        global nextID
        self._x = m["x"] + self._x
        self._y = m["y"] + self._y
        self.angle = m["angle"]
        self.mirror = m["flip"]
        self.orientation = m["orientation"]
        self.sfactor = m["scale"]
        if "name" in m.keys() :
            self.name = m["name"]
        self.selected = False
        if not new :
            self.id = m["id"]
            nextID = max(self.id+1,nextID)

class Tap(Pipe) :
    def __init__(self,m,x,y):
        Pipe.__init__(self,m,x,y)
        self.module.ports.remove(self.inPort)
        self.inPort = None
        self.inPressure = MAXPRESSURE

    def transferPressure(self):
        old_pressure = self.outPressure
        self.outPressure = self.inPressure
        if self.outPort is not None and self.outPort.connected is not None and old_pressure != self.outPressure :
            self.module.addQueue(self.outPort.connected)
            self.changed = True
        if self.changed :
            self.module.updateAbstract = True
            if self.inPressure == 0.0 or self.inPressure == 255.0 :
                self.module.updateAbstractNow = True

    def addSprites(self):
        if not self.module.module:
            img = tap_img.copy()
            img.fill(scalarToColor(self.inPressure), special_flags=pygame.BLEND_MULT)
            self.image.blit(img,(0,0))

    def scale(self,s):
        pass

class Pump(Tap) :
    def __init__(self,m,x,y):
        Tap.__init__(self,m,x,y)
        self.impeller = Impeller(self)
        if self.name == "" : self.name = "Input-"+str(self.id)
        self.label = Label(self)
        self.io = IN

    def switch(self):
        self.inPressure = MAXPRESSURE - self.inPressure
        self.changed = True

class Nozzle(Pipe):
    def __init__(self,m,x,y):
        Pipe.__init__(self,m,x,y)
        self.module.ports.remove(self.outPort)
        self.outPort = None
        self.impeller = Impeller(self)
        if self.name == "" : self.name = "Output-"+str(self.id)
        self.label = Label(self)
        self.label.mirror = -1
        self.io = OUT

    def addSprites(self):
        if not self.module.module:
            img = nozzle_img.copy()
            img.fill(scalarToColor(self.outPressure), special_flags=pygame.BLEND_MULT)
            self.image.blit(img,(0,0))

    def transferPressure(self):
        Pipe.transferPressure(self)
        if self.changed :
            self.module.updateAbstract = True
            if self.inPressure == 0.0 or self.inPressure == 255.0 :
                self.module.updateAbstractNow = True

    def scale(self,s):
        pass

class Bend(Pipe):
    def __init__(self, m, x, y):  # call Sprite intializer
        Pipe.__init__(self, m, x, y)
        self.outPort.alignedWithPipe = False

    def constructImage(self):
        Pipe.constructImage(self)
        self.outPort.rotate()

    def reflip(self) :
        pass

    def addSprites(self):
        if not self.module.module:
            if self.mirror == -1 : img = bendL_img.copy()
            else : img = bendR_img.copy()
            img.fill(scalarToColor(self.outPressure), special_flags=BLEND_MULT)
            self.image.blit(img, (0, 0))

    def scale(self, s):
        pass

    def rescale(self):
        Pipe.rescale(self)
        ang = divmod(self.angle + self.mirror * 2, 4)[1]
        offset = 1.25 * guage
        if (self.mirror == -1) :
            self.inPort.rotate()
            self.inPort.rotate()
        if ang == 0:
            self.outPort.rect.center = tuple(map(add, self.rect.center, (0, -offset + qtrGuage)))
            self.inPort.rect.center = tuple(map(add, self.rect.center, (self.mirror * offset,0)))
        elif ang == 1:
            self.outPort.rect.center = tuple(map(add, self.rect.center, (offset, 0)))
            self.inPort.rect.center = tuple(map(add, self.rect.center, (0, self.mirror * offset)))
        elif ang == 2:
            self.outPort.rect.center = tuple(map(add, self.rect.center, (0, offset)))
            self.inPort.rect.center = tuple(map(add, self.rect.center, (self.mirror * -offset, 0)))
        else:
            self.outPort.rect.center = tuple(map(add, self.rect.center, (-offset, 0)))
            self.inPort.rect.center = tuple(map(add, self.rect.center, (0, self.mirror * -offset)))

class Tee(Pipe):
    def __init__(self, m, x, y):  # call Sprite intializer
        Pipe.__init__(self,m,x,y)
        self.addCtlPort()

    def addCtlPort(self):
        self.ctlPort = OutPort(self)
        self.ctlPort.alignedWithPipe = False
        self.module.addPort(self.ctlPort)

    def constructImage(self):
        self.ctlPort.constructImage()
        self.ctlPort.rotate()
        Pipe.constructImage(self)

    def getPortPressure(self, p):
        t = Pipe.getPortPressure(self,p)
        if t is not None:
            return t
        if p == self.ctlPort : return self.outPressure
        return None

    def addSprites(self):
        if not self.module.module:
            Pipe.addSprites(self)
            img = tee_img.copy()
            img.fill(scalarToColor(self.outPressure),special_flags=BLEND_MULT)
            self.image.blit(img,(0,0))

    def reflip(self):
        Pipe.reflip(self)
        if self.mirror == -1 :
            self.ctlPort.rotate()
            self.ctlPort.rotate()

    def scale(self,s):
        pass

    def rerotate(self):
        Pipe.rerotate(self)
        self.ctlPort.rotate()

    def rescale(self):
        Pipe.rescale(self)
        ang = divmod(self.angle + self.mirror * 2,4)[1]
        #ang = self.angle
        offset = self.mirror * 2.25*guage
        if ang == 0 :
            self.ctlPort.rect.center = tuple(map(add,self.rect.center,(0,-offset)))
        elif ang == 1 :
            self.ctlPort.rect.center = tuple(map(add,self.rect.center,(offset,0)))
        elif ang == 2 :
            self.ctlPort.rect.center = tuple(map(add,self.rect.center,(0,offset)))
        else :
            self.ctlPort.rect.center = tuple(map(add,self.rect.center,(-offset,0)))

class Join(Pipe):
    def __init__(self, m, x, y):  # call Sprite intializer
        Pipe.__init__(self,m,x,y)
        self.addCtlPort()
        self.in2Pressure = 0

    def addCtlPort(self):
        self.ctlPort = OutPort(self)
        self.ctlPort.alignedWithPipe = False
        self.module.ports.remove(self.outPort)
        self.outPort = InPort(self)
        self.module.addPort(self.ctlPort)
        self.module.addPort(self.outPort)

    def constructImage(self):
        self.ctlPort.constructImage()
        self.outPort.constructImage()
        self.ctlPort.rotate()
        Pipe.constructImage(self)

    def getPortPressure(self, p):
        if p == self.inPort : return self.inPressure
        if p == self.outPort : return self.in2Pressure
        if p == self.ctlPort : return self.outPressure
        return None

    def addSprites(self):
        if not self.module.module:
            img = pipe_img.copy()
            img.fill(scalarToColor(self.in2Pressure), special_flags=pygame.BLEND_MULT)
            self.image.blit(img, (0, 0))
            img = pipe_img.copy()
            img.fill(scalarToColor(self.inPressure), special_flags=pygame.BLEND_MULT)
            self.image.blit(img, (-segment / 2, 0))
            img = tee_img.copy()
            img.fill(scalarToColor(self.outPressure),special_flags=BLEND_MULT)
            self.image.blit(img,(0,0))
            offset = (guage/2 * (self.inPressure - self.in2Pressure)/255)
            self.image.blit(merge_img,(offset,0))

    def updatePressure(self,p,src):
        if src == self.inPort :
            oldp = self.inPressure
            self.inPressure = p
            if oldp != self.inPressure:
                self.changed = True
        if src == self.outPort :
            oldp = self.in2Pressure
            self.in2Pressure = p
            if oldp != self.in2Pressure:
                self.changed = True
        if self.changed : self.transferPressure()

    def transferPressure(self):
        if self.inPort.connected is None:
            if self.inPressure > 0 : self.pressureChanged(IN)
            self.inPressure = 0
        if  self.outPort.connected is None:
            if self.in2Pressure > 0 : self.pressureChanged(IN)
            self.in2Pressure = 0
        p = self.outPressure
        self.outPressure = max(self.inPressure,self.in2Pressure)
        if p != self.outPressure : self.pressureChanged(OUT)

    def reflip(self):
        Pipe.reflip(self)
        if self.mirror == -1 :
            self.ctlPort.rotate()
            self.ctlPort.rotate()

    def scale(self,s):
        pass

    def rerotate(self):
        Pipe.rerotate(self)
        self.ctlPort.rotate()

    def rescale(self):
        Pipe.rescale(self)
        self.outPort.rotate()
        self.outPort.rotate()
        ang = divmod(self.angle + self.mirror * 2,4)[1]
        offset = self.mirror * 2.25*guage
        if ang == 0 :
            self.ctlPort.rect.center = tuple(map(add,self.rect.center,(0,-offset)))
        elif ang == 1 :
            self.ctlPort.rect.center = tuple(map(add,self.rect.center,(offset,0)))
        elif ang == 2 :
            self.ctlPort.rect.center = tuple(map(add,self.rect.center,(0,offset)))
        else :
            self.ctlPort.rect.center = tuple(map(add,self.rect.center,(-offset,0)))

class Teesistor(Tee):
    def __init__(self, m, x, y):  # call Sprite intializer
        Tee.__init__(self,m,x,y)
        self.ctlPressure = 0

    def addCtlPort(self):
        self.ctlPort = CtlPort(self)
        self.ctlPort.alignedWithPipe = False
        self.ctlPort.id = 2
        self.module.addPort(self.ctlPort)

    def updatePressure(self,p,src):
        Tee.updatePressure(self,p,src)
        oldP = self.ctlPressure
        if src == self.ctlPort :
            self.ctlPressure = p
            if oldP != self.ctlPressure :
                self.changed = True
        if self.changed : self.transferPressure()

    def getAperture(self):
        if self.ctlPressure > 0.9 * MAXPRESSURE : return 1
        elif self.ctlPressure < 0.1 * MAXPRESSURE: return 0
        else: return self.ctlPressure/MAXPRESSURE
        #return  (self.ctlPressure/MAXPRESSURE)
        #if self.ctlPressure == MAXPRESSURE : return 1
        #else : return 0

    def getPortPressure(self, p):
        t = Pipe.getPortPressure(self,p)
        if t is not None : return t
        if p == self.ctlPort : return self.ctlPressure
        return None

    def transferPressure(self):
        oldp = self.outPressure
        if self.inPort.connected is None :
            if self.inPressure > 0 : self.pressureChanged(IN)
            self.inPressure = 0
        if self.ctlPort.connected is None :
            if self.ctlPressure > 0 : self.pressureChanged(IN)
            self.ctlPressure = 0
        aperture = self.getAperture()
        if aperture == 0 :
            self.outPressure = 0
        else :
            src =  self.inPressure
            sink = self.outPressure
            self.outPressure = equalizePressure(src,sink,aperture)
        if oldp != self.outPressure :
            self.pressureChanged(OUT)

    def constructImage(self) :
        self.ctlPort.constructImage()
        self.ctlPort.rotate()
        self.ctlPort.rotate()
        self.ctlPort.rotate()
        Pipe.constructImage(self)

    def drawSpring(self,compression,img):
        fudge = 3
        x0 = guage+fudge
        y0 = halfGuage+fudge
        yspace = 1.5*guage - compression - (2 * fudge)
        c = pygame.Color(210,210,210)
        #https: // math.stackexchange.com / questions / 2216407 / equation - of - a - 2d - helix
        pygame.gfxdraw.line(img, x0, y0, x0+guage-2*fudge, int(y0+yspace/5), c)
        pygame.gfxdraw.line(img, x0+guage-2*fudge, int(y0+yspace/5), x0, int(y0+2*yspace/5),c)
        pygame.gfxdraw.line(img, x0, int(y0+2*yspace/5), x0+guage-2*fudge, int(y0+3*yspace/5),c)
        pygame.gfxdraw.line(img, x0+guage-2*fudge, int(y0+3*yspace/5), x0, int(y0+(4*yspace/5)),c)
        pygame.gfxdraw.line(img, x0, int(y0+(4*yspace/5)), x0+guage-2*fudge, int(y0+(yspace)),c)

    def addSprites(self):
        if not self.module.module:
            Pipe.addSprites(self)
            img = teesistor_img.copy()
            img.fill(scalarToColor(self.ctlPressure),special_flags=BLEND_MULT)
            a = self.getAperture()
            compression = int(a * guage)
            self.drawSpring(compression,img)
            self.image.blit(img,(0,0))
            self.image.blit(ncvalve_img,(0,-compression))

class Teeverter(Teesistor):
    def __init__(self, m, x, y):  # call Sprite intializer
        Teesistor.__init__(self,m,x,y)

    def addSprites(self):
        if not self.module.module:
            Pipe.addSprites(self)
            img = teesistor_img.copy()
            img.fill(scalarToColor(self.ctlPressure),special_flags=BLEND_MULT)
            a = self.getAperture()
            compression = int((1 - a) * guage)
            self.drawSpring(compression,img)
            self.image.blit(img,(0,0))
            self.image.blit(novalve_img,(0,-compression))

    def getAperture(self):
        if self.ctlPressure > 0.9 * MAXPRESSURE : return 0
        elif self.ctlPressure < 0.1 * MAXPRESSURE: return 1
        else: return 1 - self.ctlPressure/MAXPRESSURE
        #return  1 - (self.ctlPressure/MAXPRESSURE)
        #if self.ctlPressure == 0 : return 1
        #else : return 0

def shiftPressed() :
    keyState = pygame.key.get_pressed()
    return(keyState[pygame.K_LSHIFT] or keyState[pygame.K_RSHIFT])

def rectFromTwoPoints(p1,p2):
    ulx = min(p1[0],p2[0])
    uly = min(p1[1],p2[1])
    w = abs(p1[0]-p2[0])
    h = abs(p1[1]-p2[1])
    return pygame.Rect(ulx,uly,w,h)

def onHandle(point) :
    for h in currentModule.handles :
        if h.rect.collidepoint(point) :
            return (h)
    return None

def onImpeller(point) :
    for i in currentModule.impellers :
        rect = pygame.Rect.inflate(i.rect,20-i.rect.width,20-i.rect.height)
        if rect.collidepoint(point) :
            return (i)
    return None

label_editor = None
editing_pipe = None
def onLabel(point) :
    global label_editor,editing_pipe
    if currentModule is not None:
        for i in currentModule.labels :
            if i.rect.collidepoint(point) :
                new_rect = pygame.Rect((0, 0), (160, 20))
                new_rect.center = i.rect.center
                if label_editor is not None : label_editor.kill()
                label_editor = pg.elements.UITextEntryLine(new_rect, manager)
                label_editor.set_text(i.pipe.name)
                editing_pipe = i.pipe
                return editing_pipe

def onGUI(point) :
    global label_editor, editing_pipe
    for i in manager.get_sprite_group() :
        if (i.rect.width != screen_w) :
            if i.rect.collidepoint(point) : return True
    return False

def moveSelected(deltaPos) :
    for h in currentModule.handles :
        if (h.component.selected) :
            h.move(deltaPos)

pipe_img, pipe_rect = load_image("halfpipe.png")
full_pipe_img, full_pipe_rect = load_image("pipe.png")
tee_img, tee_rect = load_image("tee.png")
tap_img, tap_rect = load_image("tap.png")
novalve_img, novalve_rect = load_image("NOvalve.png")
ncvalve_img, ncvalve_rect = load_image("NCvalve.png")
impeller_img, impeller_rect = load_image("impeller.png")
nozzle_img, nozzle_rect = load_image("nozzle.png")
bendR_img, bendR_rect = load_image("bendR.png")
bendL_img, bendL_rect = load_image("bendL.png")
merge_img, merge_rect = load_image("pusherL.png")
teesistor_img, teesistor_rect = load_image("teesistor.png")

background = pygame.Surface(screen.get_size())
background = background.convert()
background.fill((160, 160, 160))
screen.blit(background, (0, 0))
pygame.display.flip()
Clock = pygame.time.Clock()

def makeNewModule() :
    m = Module()
    # Pipe(currentModule,200,200)
    Pipe(m,50,600).constructImage()
    Teesistor(m,130,600).constructImage()
    Teeverter(m,210,600).constructImage()
    Tee(m,290,600).constructImage()
    Tap(m,370,600).constructImage()
    Pump(m,450,600).constructImage()
    Nozzle(m,530,600).constructImage()
    Bend(m,610,600).constructImage()
    Join(m,690,600).constructImage()
    m.initUndoStack()
    return m

def rotateSelected() :
    for h in currentModule.handles :
            if h.component.selected :
                h.component.rotate()

def flipSelected() :
    for h in currentModule.handles :
            if h.component.selected :
                h.component.flip()

def growSelected() :
    for h in currentModule.handles :
            if h.component.selected :
                h.component.scale(1)

def shrinkSelected() :
    for h in currentModule.handles :
            if h.component.selected :
                h.component.scale(-1)

classes = {}
classes["Pipe"] = Pipe
classes["Teesistor"] = Teesistor
classes["Teeverter"] = Teeverter
classes["Tee"] = Tee
classes["Tap"] = Tap
classes["Pump"] = Pump
classes["Nozzle"] = Nozzle
classes["Bend"] = Bend
classes["Join"] = Join

def loadModule(name) :
    file = os.path.join("projects", name+".json")
    with open(file, 'r') as f:
        datastore = json.load(f)
        cm = Module()
        cm.loadSerializationMap(datastore)
        return cm

loaded_modules = {}
mods = []
for file in os.listdir("projects"):
    if file.endswith(".json"):
        name = file.split('.')[0]
        mods.append(name)
        loaded_modules[name] = loadModule(name)
module_list = pg.elements.UIDropDownMenu(options_list=mods, starting_option="Load", manager=manager,
                                         relative_rect=pygame.Rect((screen_w - ui_width - 10, 70),
                                                                   (ui_width, ui_height)))
add_module = pg.elements.UIDropDownMenu(options_list=mods, starting_option="Add Instance", manager=manager,
                                         relative_rect=pygame.Rect((screen_w - ui_width - 10, 100),
                                                                   (ui_width, ui_height)))
add_module.kill()

gui_elements.append(module_list)
gui_elements.append(add_module)


def duplicateSelected() :
    for h in currentModule.handles :
            if h.component.selected :
                h.select(False)
                h.applyGhostHandle()
                m = h.component.getSerializationMap()
                p = currentModule.loadComponent(m, 2 * guage, 2 * guage)
                p.handle.select(True)

copyBuffer = []
pasteCount = 0
def copySelected() :
    global copyBuffer, pasteCount
    copyBuffer = []
    pasteCount = 0
    for h in currentModule.handles :
            if h.component.selected :
                copyBuffer.append(h.component.getSerializationMap())

def pasteSelected() :
    global pasteCount, copyBuffer
    pasteCount = pasteCount + 1
    for h in currentModule.handles :
            if h.component.selected :
                h.select(False)
                h.applyGhostHandle()
    for m in copyBuffer :
                p = currentModule.loadComponent(m, pasteCount * 2 * guage, pasteCount * 2 * guage)
                p.handle.select(True)

def duplicateSelected() :
    for h in currentModule.handles :
            if h.component.selected :
                h.select(False)
                h.applyGhostHandle()
                m = h.component.getSerializationMap()
                p = currentModule.loadComponent(m, 2 * guage, 2 * guage)
                p.handle.select(True)

def deleteSelected() :
    for h in currentModule.handles :
            if h.component.selected : currentModule.removePipe(h.component)

def undo() :
    currentModule.undo()

def redo() :
    currentModule.redo()

def turnOffDecorations() :
    global decorationsVisible
    if currentModule :
        for p in currentModule.pipes :
            p.turnOffDecorations()
            decorationsVisible = False

def turnOnDecorations() :
    global decorationsVisible
    if not decorationsVisible and currentModule is not None:
        for p in currentModule.pipes :
            p.turnOnDecorations()
            decorationsVisible = True

def togglePause() :
    global pauseEqualize
    pauseEqualize = not pauseEqualize

def keyMap(key) :
    switcher = {
        ord('r'): rotateSelected,
        ord('f'): flipSelected,
        ord('g'): growSelected,
        ord('s'): shrinkSelected,
        ord('d'): duplicateSelected,
        ord('c'): copySelected,
        ord('v'): pasteSelected,
        ord('z'): undo,
        ord('y'): redo,
        ord('q'): turnOffDecorations,
        ord('p'): togglePause,
        127: deleteSelected
    }
    func = switcher.get(key, lambda: "unknown command")
    func()

selectBox = None
lastEvent = pygame.time.get_ticks()

while 1:
    time_delta = Clock.tick(60)/1000.0
    now = pygame.time.get_ticks()
    if now - lastEvent > 2000: turnOffDecorations()
    for event in pygame.event.get():
        lastEvent = pygame.time.get_ticks()
        if event.type == pygame.USEREVENT:
            if event.user_type == 'ui_button_pressed':
                if event.ui_element == new_button:
                    currentModule = makeNewModule()
                    module_name.set_text("")
            if event.user_type == 'ui_drop_down_menu_changed' :
                if event.ui_element == module_list :
                    currentModule = loaded_modules[module_list.selected_option]
                    module_name.set_text(module_list.selected_option)
                    module_name.unselect()
                    module_list.selected_option = "Edit"
                elif event.ui_element == add_module :
                    loaded_modules[add_module.selected_option].getInstance()
                    add_module.unselect()
                    add_module.selected_option = "Add Instance"
                elif event.ui_element == command_list :
                    cmd = ord(command_list.selected_option[-1:])
                    command_list.selected_option = "Commands"
                    if currentModule : keyMap(cmd)
            if event.user_type == 'ui_text_entry_finished' :
                if event.ui_element == module_name :
                    currentModule.save()
                    currentModule = loadModule(module_name.text)
                    loaded_modules[module_name.text] = currentModule
                    if module_name.text not in module_list.options_list : module_list.options_list.append(module_name.text)
                    module_list.selected_option = "Load"
                    module_name.unselect()
                if label_editor is not None and event.ui_element == label_editor :
                    if editing_pipe is not None :
                        editing_pipe.setName(label_editor.text)
                        currentModule.changed = True
                    label_editor.kill()
                    label_editor = None
                    editing_pipe = None
        if currentModule is not None :
            if event.type == pygame.QUIT:
                quit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                quit()
            elif event.type == pygame.MOUSEBUTTONDOWN and not onGUI(event.pos):
                pressed1, pressed2, pressed3 = pygame.mouse.get_pressed()
                downPos = lastPos = event.pos
                if pressed1 :
                    if label_editor is not None :
                        if editing_pipe is not None:
                            editing_pipe.setName(label_editor.text)
                            currentModule.changed = True
                        label_editor.kill()
                        label_editor = None
                    currentHandle = onHandle(downPos)
                    currentImpeller = onImpeller(downPos)
                    editing_pipe = onLabel(downPos)
            elif event.type == pygame.MOUSEMOTION and not onGUI(event.pos) :
                turnOnDecorations()
                if (currentHandle) :
                    if not currentHandle.component.selected and not shiftPressed():
                        for h in currentModule.handles:
                            if h != currentHandle:
                                h.select(False)
                                h.applyGhostHandle()
                    currentHandle.select(True)
                    currentHandle.applySelectedHandle()
                pressed1, pressed2, pressed3 = pygame.mouse.get_pressed()
                if pressed1 :
                    if currentHandle:
                        moveSelected(tuple(map(sub, event.pos, lastPos)))
                        #lastPos = event.pos
                    elif downPos is not None : selectBox = rectFromTwoPoints(downPos,event.pos)
                else :
                    for h in currentModule.handles :
                        if not h.component.selected :
                            if h.rect.collidepoint(event.pos) : h.applyOverHandle()
                            else : h.applyGhostHandle()
            elif event.type == pygame.MOUSEBUTTONUP and not onGUI(event.pos) :
                if selectBox :
                    for h in currentModule.handles :
                        if h.rect.colliderect(selectBox) :
                            h.select(True)
                            h.applySelectedHandle()
                        elif not shiftPressed():
                            h.select(False)
                            h.applyGhostHandle()
                elif currentHandle:
                    if (downPos == event.pos) :
                        currentHandle.select(not currentHandle.component.selected)
                        if not shiftPressed():
                            for h in currentModule.handles:
                                if h != currentHandle:
                                    h.select(False)
                                    h.applyGhostHandle()
                    if currentHandle.component.selected : currentHandle.applySelectedHandle()
                    else : currentHandle.applyOverHandle()
                else :
                    for h in currentModule.handles :
                        h.select(False)
                        h.applyGhostHandle()
                if currentImpeller is not None :
                    currentImpeller.switch()
                downPos = lastPos = currentHandle = currentImpeller = selectBox = None
            elif event.type == pygame.KEYDOWN :
                keyMap(event.key)
        manager.process_events(event)
    manager.update(time_delta)

    if currentModule is not None :
        currentModule.update()
        currentModule.impellers.update()
        currentModule.labels.update()
        currentModule.handles.update()
        screen.blit(background, (0, 0))
        currentModule.pipes.draw(screen)
        currentModule.instances.draw(screen)
        currentModule.handles.draw(screen)
        currentModule.impellers.draw(screen)
        currentModule.ports.draw(screen)
        currentModule.labels.draw(screen)
        modules = pygame.sprite.RenderPlain()
        modules.add(currentModule)
        modules.draw(screen)
        if selectBox : pygame.gfxdraw.rectangle(screen, selectBox, (255, 255, 255))
        pygame.gfxdraw.rectangle(screen,(currentModule.rect.left,currentModule.rect.bottom + 5,currentModule.rect.width,10),(255,255,255))
        pygame.gfxdraw.box(screen, (currentModule.rect.left,currentModule.rect.bottom + 5,currentModule.rect.width*(len(currentModule.changeQueue)/len(currentModule.ports)),10),(255,0,0))
    manager.draw_ui(screen)
    pygame.display.flip()

