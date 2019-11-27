PGraphics alphaG;

float yoff = 0.0;        // 2nd dimension of perlin noise
float maxPressure = 255;
int guage = 20;
int grid = guage/2;  
int Teelen = 2*guage;
int segment = 3*guage;
int pumpL = guage+guage/2;
int pumpW = pumpL/5;
int ctlZ = 26;
int ctlY = 25;
color pipeWall = color(0);
color acquamarine = color(0, 255, 191);
int count = 0;
int l = 60;
int w = 100;
int cx = l/2;
int cy = w/2;
ArrayList colors = new ArrayList();

void setup() {
  size(60,100); 
  // create an extra pgraphics object for rendering on a transparent background 
   
  // background will be transparent in the png-file 
  background(255,255,0,1);
  
  for (int i = guage/2; i < guage; i++) {
    float inter = map(i, guage/2, guage, 0, 1);
    inter = cos(inter*PI/2);
    color c = lerpColor(color(0), color(255), inter);
    colors.add(c);
  }
  println("Gradient has ",colors.size(),"colors");
}

void drawPipe() { 
    alphaG.translate(cx,cy);
    rectGradientY(-segment/2,-guage/2,segment/2,guage);  // input side
    rectGradientY(0,-guage/2,segment/2,guage);  // output side
}

void drawWheel() { 
    alphaG.translate(cx,cy);
    angleGradientY(0,0);  // input side
}

void drawHalfPipe() { 
    alphaG.translate(cx,cy);
    rectGradientY(0,-guage/2,segment/2,guage);  // input side
}

void drawGuagePipeL() { 
    fill(scalarToColor(0));
    rectGradientY(guage/2,-guage/2,guage,guage);  // input side
}

void drawGuagePipeR() { 
    fill(scalarToColor(0));
    rectGradientY(-cx,-guage/2,guage,guage);  // input side
}

void drawTeesistor() {
    alphaG.translate(cx,cy);
    rectGradientX(-guage/2,guage/2,guage,Teelen);
}

void drawImpeller() {
  float size = guage/1.5;
  alphaG.translate(cx,cy);
  alphaG.stroke(0);
  alphaG.strokeWeight(2);
  alphaG.ellipseMode(CENTER);
  alphaG.fill(255);
  alphaG.circle(0,0,size);
  alphaG.noFill();
  for (int i = 0; i<6;i++) {
      alphaG.push();
      alphaG.translate(size/2,0);
      alphaG.arc(0,0,size,size,0,HALF_PI);
      alphaG.pop();
      alphaG.rotate(TWO_PI/6);
  }
}

void drawValveBodyNC() {
  alphaG.push();
  alphaG.translate(cx,cy);
  alphaG.fill(200,220,0);
  alphaG.stroke(0);
  alphaG.strokeWeight(1);
  alphaG.rect((-guage/2)+1,-(guage/2),guage-2,guage+guage/4);
  alphaG.rect((-guage/2)+1,(guage+guage/4),guage-2,guage/4);
    
  alphaG.pop();
}

void drawValveBodyNO() {
  alphaG.push();
  alphaG.translate(cx,cy);
  alphaG.fill(200,0,220);
  alphaG.stroke(0);
  alphaG.strokeWeight(1);
  alphaG.rect((-guage/2)+1,-(guage/2),guage-2,guage/4);
  alphaG.rect((-guage/2)+1,guage/4,guage-2,guage+guage/4);   
  alphaG.pop();
}

void drawSpringCase() {
  alphaG.push();
  alphaG.translate(cx,cy);
  alphaG.strokeWeight(4);
  alphaG.stroke(0);
  float ydim = 1.5*guage;
  alphaG.line(-guage/2,ydim/2,-guage/2,-ydim/2);
  alphaG.line(-guage/2,-ydim/2,guage/2,-ydim/2);
  alphaG.line(guage/2,-ydim/2,guage/2,ydim/2);
  alphaG.pop();
}

void drawValveSprings() {
    alphaG.push();
    int coils = 5;
    float space = 1.5*guage;
    float halfcoil = space/(coils + 1);
    //float anchorY = (-1.5*guage - guage/2 + halfcoil);
    float anchorY = -space/2;
    float anchorX = 0;
    alphaG.translate(cx,cy);
    alphaG.stroke(255);
    alphaG.noFill();
    for (int i = 0; i<coils; i++){
      alphaG.ellipse(anchorX,anchorY+((i*halfcoil)),guage-6,2*halfcoil);
    }
    alphaG.pop();
}

void drawBendL() {
  alphaG.translate(cx,cy);
  drawGuagePipeL();
  rectGradientX(-guage/2,guage/2,guage,guage); 
  alphaG.translate(guage/2,guage/2);
  dualArcGradient(2*guage, PI,3*PI/2);
}

void drawPusherValveL() {
  alphaG.translate(cx,cy);
  alphaG.fill(#F04507);
  alphaG.triangle(-guage,-guage/2,-guage/2,guage/2,-guage/2,-guage/2);;
}

void drawPusherValveR() {
  alphaG.translate(cx,cy);
  alphaG.fill(#F04507);
  alphaG.triangle(guage,-guage/2,guage/2,guage/2,guage/2,-guage/2);;
}

void drawBendR() {
  alphaG.translate(cx,cy);
  drawGuagePipeR();
  rectGradientX(-guage/2,guage/2,guage,guage); 
  alphaG.translate(guage/2,guage/2);
  alphaG.translate(-guage,0);
  dualArcGradient(2*guage, 3*PI/2, TWO_PI);
}

void drawTee() {
  alphaG.translate(cx,cy);
  rectGradientXFlange(-guage/2,guage/2,guage,Teelen);
}

void drawTap() {
  arcGradient(guage, PI/2,3*PI/2);
}
  


void draw() {
   size(60,100);
   alphaG = createGraphics(width,height);

  // draw into the pgraphics object
  if (count == 0) {
    alphaG.beginDraw();
    drawPipe();
    alphaG.endDraw();
   
    // draw the second renderer into the window, so we can see something 
    image(alphaG, 0,0);
    alphaG.save("pipe.png"); 
    println("pipe.png saved.");
  } else if (count == 1) {    
    alphaG.beginDraw();
    //drawPipe();
    drawTee();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("tee.png"); 
    println("tee.png saved.");
  }  else if (count == 2) {    
    alphaG.beginDraw();
    drawHalfPipe();
    drawTap();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("tap.png"); 
    println("tap.png saved.");
  } else if (count == 3) {
    alphaG.beginDraw();
    drawBendL();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("bendL.png"); 
    println("bendL.png saved.");
  } else if (count == 4) {
    alphaG.beginDraw();
    //drawPipe();
    drawTeesistor();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("teesistor.png"); 
    println("teesistor.png saved.");
  } else if (count == 5) {
    alphaG.beginDraw();
    drawValveBodyNC();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("NCvalve.png"); 
    println("NCvalve.png saved.");
  } else if (count == 6) {
    alphaG.beginDraw();
    drawValveBodyNO();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("NOvalve.png"); 
    println("NOvalve.png saved.");
  } else if (count == 7) {
    alphaG.beginDraw();
    drawValveSprings();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("springs.png"); 
    println("springs.png saved.");
  } else if (count == 8) {
    alphaG.beginDraw();
    drawBendR();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("bendR.png"); 
    println("bendR.png saved.");
  } else if (count == 9) {
    alphaG.beginDraw();
    drawSpringCase();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("springCase.png"); 
    println("sringCase.png saved.");
  } else if (count == 10) {
    alphaG.beginDraw();
    drawHalfPipe();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("halfPipe.png"); 
    println("halfPipe.png saved.");
  } else if (count == 11) {
    alphaG.beginDraw();
    drawPusherValveL();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("pusherL.png"); 
    println("pusherL.png saved.");
  } else if (count == 12) {
    alphaG.beginDraw();
    drawPusherValveR();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("pusherR.png"); 
    println("pusherR.png saved.");
  } else if (count == 13) {
    alphaG.beginDraw();
    drawWheel();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("nozzle.png"); 
    println("nozzle.png saved.");
  } else if (count == 14) {
    alphaG.beginDraw();
    drawImpeller();
    alphaG.endDraw(); 
    image(alphaG, 0,0);
    alphaG.save("impeller.png"); 
    println("impeller.png saved.");
  }
  count = count+1;
}
 
void keyPressed() {
   alphaG.save("alphatest.png"); 
   println("alphatest.png saved.");
}


void arcGradient(int dia, float start, float stop) {
  alphaG.push();
  alphaG.ellipseMode(CENTER);
  alphaG.noFill();
  int i = 1;
  for (int j = 0; j < colors.size(); j++ ){
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.arc(0,0,2*i-1,2*i-1,start,stop);
    i++;
  }
  alphaG.pop();
}

void dualArcGradient(int dia, float start, float stop) {
  alphaG.push();
  alphaG.ellipseMode(CENTER);
  //ArrayList colors = new ArrayList();
  alphaG.noFill();
  int i = colors.size()+1;
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.arc(0,0,2*i-1,2*i-1,start,stop);
    println("dia",i);
    i++;
  }
  i = colors.size();
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.arc(0,0,2*i,2*i,start,stop);
    println("dia",i);
    i--;
  }
  alphaG.pop();
}

void rectGradientX(int x, int y, int w, int h) {
  alphaG.push();
  
  int i = x + w/2;
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.line(i,y,i,y+h);
    i++;
  }
  i = x + w/2-1;
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.line(i,y,i,y+h);
    i--;
  }
  alphaG.pop();
}

void rectGradientXFlange(int x, int y, int w, int h) {
  alphaG.push();
  float depth = colors.size()/2;
  int i = x + w/2;
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.line(i,y-(depth-(j/2)),i,y+h);
    i++;
  }
  i = x + w/2-1;
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.line(i,y-(depth-(j/2)),i,y+h);
    i--;
  }
  alphaG.pop();
}

void angleGradientY(int x, int y) {
  alphaG.push();
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.line(x,y+j,x+j,y);
    println("index ",j,x,y+j,x+j,y);
  }
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.line(x,y-j,x+j,y);
    println("index ",j,x,y-j,x+j,y);
  }
  alphaG.pop();
}

void rectGradientY(int x, int y, int w, int h) {
  alphaG.push();
  int i = y+h/2;
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.line(x,i,x+w,i);
    //println("index ",i);
    i++;
  }
  i = y + h/2-1;
  for (int j = 0; j < colors.size(); j++) {
    color c = (color)colors.get(j);
    alphaG.stroke(c);
    alphaG.line(x,i,x+w,i);
    //println("index ",i);
    i--;
  }
  alphaG.pop();
}

color scalarToColor(float f) {
  color c1 = color(255);
  color c2 = acquamarine;

  f = f/255;
  color c = lerpColor(c1, c2, f);
  return c;
}
