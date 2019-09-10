
(function(window){
    
    // A Javascript 2D vector library
    // conventions :
    // method that returns a float value do not modify the vector
    // method that implement operators return a new vector with the modifications without
    // modifying the calling vector or the parameters.
    // 
    //      v3 = v1.add(v2); // v3 is set to v1 + v2, v1, v2 are not modified
    //
    // methods that take a single vector as a parameter are usually also available with
    // q '_xy' suffix. Those method takes two floats representing the x,y coordinates of
    // the vector parameter and allow you to avoid to needlessly create a vector object : 
    //
    //      v2 = v1.add(new Vec2(3,4));
    //      v2 = v1.add_xy(3,4);             //equivalent to previous line
    //
    // angles are in radians by default but method that takes angle as parameters 
    // or return angle values usually have a variant with a '_deg' suffix that works in degrees
    //
     
    // The 2D vector object 
    function Vec2(x,y){
        this.x = x;
        this.y = y;
    }

    window.Vec2 = Vec2;
    
    // Multiply a number expressed in radiant by rad2deg to convert it in degrees
    var rad2deg = 57.29577951308232;
    // Multiply a number expressed in degrees by deg2rad to convert it to radiant
    var deg2rad = 0.017453292519943295;
    // The numerical precision used to compare vector equality
    var epsilon   = 0.0000001;

    // This static method creates a new vector from polar coordinates with the angle expressed
    // in degrees
    Vec2.new_polar_deg = function(len,angle){
        var v = new Vec2(len,0);
        return v.rotate_deg(angle);
    };
    // This static method creates a new vector from polar coordinates with the angle expressed in
    // radians
    Vec2.new_polar = function(len,angle){
        var v = new Vec2(len,0);
        v.rotate(angle);
        return v;
    };
    // returns the length or modulus or magnitude of the vector
    Vec2.prototype.len = function(){
        return Math.sqrt(this.x*this.x + this.y*this.y);
    };
    // returns the squared length of the vector, this method is much faster than len()
    Vec2.prototype.len_sq = function(){
        return this.x*this.x + this.y*this.y;
    };
    // return the distance between this vector and the vector v
    Vec2.prototype.dist = function(v){
        var dx = this.x - v.x;
        var dy = this.y - v.y;
        return Math.sqrt(dx*dx + dy*dy);
    };
    // return the distance between this vector and the vector of coordinates (x,y)
    Vec2.prototype.dist_xy = function(x,y){
        var dx = this.x - x;
        var dy = this.y - y;
        return Math.sqrt(dx*dx + dy*dy);
    };
    // return the squared distance between this vector and the vector and the vector v
    Vec2.prototype.dist_sq = function(v){
        var dx = this.x - v.x;
        var dy = this.y - v.y;
        return dx*dx + dy*dy;
    };
    // return the squared distance between this vector and the vector of coordinates (x,y)
    Vec2.prototype.dist_sq_xy = function(x,y){
        var dx = this.x - x;
        var dy = this.y - y;
        return dx*dx + dy*dy;
    };
    // return the dot product between this vector and the vector v
    Vec2.prototype.dot = function(v){
        return this.x*v.x + this.y*v.y;
    };
    // return the dot product between this vector and the vector of coordinate (x,y)
    Vec2.prototype.dot_xy = function(x,y){
        return this.x*x + this.y*y;
    };
    // return a new vector with the same coordinates as this 
    Vec2.prototype.clone = function(){
        return new Vec2(this.x,this.y);
    };
    // return the sum of this and vector v as a new vector
    Vec2.prototype.add = function(v){
        return new Vec2(this.x+v.x,this.y+v.y);
    };
    // return the sum of this and vector (x,y) as a new vector
    Vec2.prototype.add_xy = function(x,y){
        return new Vec2(this.x+x,this.y+y);
    };
    // returns (this - v) as a new vector where v is a vector and - is the vector subtraction
    Vec2.prototype.sub = function(v){
        return new Vec2(this.x-v.x,this.y-v.y);
    };
    // returns (this - (x,y)) as a new vector where - is vector subtraction
    Vec2.prototype.sub_xy = function(x,y){
        return new Vec2(this.x-x,this.y-y);
    };
    // return (this * v) as a new vector where v is a vector and * is the by component product
    Vec2.prototype.mult = function(v){
        return new Vec2(this.x*v.x,this.y*v.y);
    };
    // return (this * (x,y)) as a new vector where * is the by component product
    Vec2.prototype.mult_xy = function(x,y){
        return new Vec2(this.x*x,this.y*y);
    };
    // return this scaled by float f as a new fector
    Vec2.prototype.scale = function(f){
        return new Vec2(this.x*f, this.y*f);
    };
    // return the negation of this vector
    Vec2.prototype.neg = function(f){
        return new Vec2(-this.x,-this.y);
    };
    // return this vector normalized as a new vector
    Vec2.prototype.normalize = function(){
        var len = this.len();
        if(len == 0){
            return new Vec2(0,1);
        }else if(len != 1){
            return this.scale(1.0/len);
        }
        return new Vec2(this.x,this.y);
    };
    // return a new vector with the same direction as this vector of length float l. (negative values of l will invert direction)
    Vec2.prototype.set_len = function(l){
        return this.normalize().scale(l);
    };
    // return the projection of this onto the vector v as a new vector
    Vec2.prototype.project = function(v){
        return v.set_len(this.dot(v));
    };
    // return a string representation of this vector
    Vec2.prototype.toString = function(){
        var str = "";
        str += "[";
        str += this.x;
        str += ",";
        str += this.y;
        str += "]";
        return str;
    };
    //return this vector counterclockwise rotated by rad radians as a new vector
    Vec2.prototype.rotate = function(rad){
        var c = Math.cos(rad);
        var s = Math.sin(rad);
        var px = this.x * c - this.y *s;
        var py = this.x * s + this.y *c;
        return new Vec2(px,py);
    };
    //return this vector counterclockwise rotated by deg degrees as a new vector
    Vec2.prototype.rotate_deg = function(deg){
        return this.rotate(deg * deg2rad);
    };
    //linearly interpolate this vector towards the vector v by float factor alpha.
    // alpha == 0 : does nothing
    // alpha == 1 : sets this to v
    Vec2.prototype.lerp = function(v,alpha){
        var inv_alpha = 1 - alpha;
        return new Vec2(    this.x * inv_alpha + v.x * alpha,
                            this.y * inv_alpha + v.y * alpha    );
    };
    // returns the angle between this vector and the vector (1,0) in radians
    Vec2.prototype.angle = function(){
        return Math.atan2(this.y,this.x);
    };
    // returns the angle between this vector and the vector (1,0) in degrees
    Vec2.prototype.angle_deg = function(){
        return Math.atan2(this.y,this.x) * rad2deg;
    };
    // returns true if this vector is equal to the vector v, with a tolerance defined by the epsilon module constant
    Vec2.prototype.equals = function(v){
        if(Math.abs(this.x-v.x) > epsilon){
            return false;
        }else if(Math.abs(this.y-v.y) > epsilon){
            return false;
        }
        return true;
    };
    // returns true if this vector is equal to the vector (x,y) with a tolerance defined by the epsilon module constant
    Vec2.prototype.equals_xy = function(x,y){
        if(Math.abs(this.x-x) > epsilon){
            return false;
        }else if(Math.abs(this.y-y) > epsilon){
            return false;
        }
        return true;
    };
})(window);

(function(window){
    // A Bounding Shapes Library


    // A Bounding Ellipse
    // cx,cy : center of the ellipse
    // rx,ry : radius of the ellipse
    function BEllipse(cx,cy,rx,ry){
        this.type = 'ellipse';
        this.x = cx-rx;     // minimum x coordinate contained in the ellipse     
        this.y = cy-ry;     // minimum y coordinate contained in the ellipse
        this.sx = 2*rx;     // width of the ellipse on the x axis
        this.sy = 2*ry;     // width of the ellipse on the y axis
        this.hx = rx;       // half of the ellipse width on the x axis
        this.hy = ry;       // half of the ellipse width on the y axis
        this.cx = cx;       // x coordinate of the ellipse center
        this.cy = cy;       // y coordinate of the ellipse center
        this.mx = cx + rx;  // maximum x coordinate contained in the ellipse
        this.my = cy + ry;  // maximum x coordinate contained in the ellipse
    }
    window.BEllipse = BEllipse;

    // returns an unordered list of vector defining the positions of the intersections between the ellipse's
    // boundary and a line segment defined by the start and end vectors a,b
    BEllipse.prototype.collide_segment = function(a,b){
        // http://paulbourke.net/geometry/sphereline/
        var collisions = [];

        if(a.equals(b)){  //we do not compute the intersection in this case. TODO ?     
            return collisions;
        }

        // make all computations in a space where the ellipse is a circle 
        // centered on zero
        var c = new Vec2(this.cx,this.cy);
        a = a.sub(c).mult_xy(1/this.hx,1/this.hy);
        b = b.sub(c).mult_xy(1/this.hx,1/this.hy);


        if(a.len_sq() < 1 && b.len_sq() < 1){   //both points inside the ellipse
            return collisions;
        }

        // compute the roots of the intersection
        var ab = b.sub(a);
        var A = (ab.x*ab.x + ab.y*ab.y);
        var B = 2*( ab.x*a.x + ab.y*a.y);
        var C = a.x*a.x + a.y*a.y - 1;
        var u  = B * B - 4*A*C;
        
        if(u < 0){
            return collisions;
        }

        u = Math.sqrt(u);
        var u1 = (-B + u) / (2*A);
        var u2 = (-B - u) / (2*A);

        if(u1 >= 0 && u1 <= 1){
            var pos = a.add(ab.scale(u1));
            collisions.push(pos);
        }
        if(u1 != u2 && u2 >= 0 && u2 <= 1){
            var pos = a.add(ab.scale(u2));
            collisions.push(pos);
        }
        for(var i = 0; i < collisions.length; i++){
            collisions[i] = collisions[i].mult_xy(this.hx,this.hy);
            collisions[i] = collisions[i].add_xy(this.cx,this.cy);
        }
        return collisions;
    };
    
    // A bounding rectangle
    // x,y the minimum coordinate contained in the rectangle
    // sx,sy the size of the rectangle along the x,y axis
    function BRect(x,y,sx,sy){
        this.type = 'rect';
        this.x = x;              // minimum x coordinate contained in the rectangle  
        this.y = y;              // minimum y coordinate contained in the rectangle
        this.sx = sx;            // width of the rectangle on the x axis
        this.sy = sy;            // width of the rectangle on the y axis
        this.hx = sx/2;          // half of the rectangle width on the x axis
        this.hy = sy/2;          // half of the rectangle width on the y axis
        this.cx = x + this.hx;   // x coordinate of the rectangle center
        this.cy = y + this.hy;   // y coordinate of the rectangle center
        this.mx = x + sx;        // maximum x coordinate contained in the rectangle
        this.my = y + sy;        // maximum x coordinate contained in the rectangle
    }

    window.BRect = BRect;
    // Static method creating a new bounding rectangle of size (sx,sy) centered on (cx,cy)
    BRect.new_centered = function(cx,cy,sx,sy){
        return new BRect(cx-sx/2,cy-sy/2,sx,sy);
    };
    //intersect line a,b with line c,d, returns null if no intersection
    function line_intersect(a,b,c,d){
        // http://paulbourke.net/geometry/lineline2d/
        var f = ((d.y - c.y)*(b.x - a.x) - (d.x - c.x)*(b.y - a.y)); 
        if(f == 0){
            return null;
        }
        f = 1 / f;
        var fab = ((d.x - c.x)*(a.y - c.y) - (d.y - c.y)*(a.x - c.x)) * f ;
        if(fab < 0 || fab > 1){
            return null;
        }
        var fcd = ((b.x - a.x)*(a.y - c.y) - (b.y - a.y)*(a.x - c.x)) * f ;
        if(fcd < 0 || fcd > 1){
            return null;
        }
        return new Vec2(a.x + fab * (b.x-a.x), a.y + fab * (b.y - a.y) );
    }

    // returns an unordered list of vector defining the positions of the intersections between the ellipse's
    // boundary and a line segment defined by the start and end vectors a,b

    BRect.prototype.collide_segment = function(a,b){
        var collisions = [];
        var corners = [ new Vec2(this.x,this.y), new Vec2(this.x,this.my), 
                        new Vec2(this.mx,this.my), new Vec2(this.mx,this.y) ];
        var pos = line_intersect(a,b,corners[0],corners[1]);
        if(pos) collisions.push(pos);
        pos = line_intersect(a,b,corners[1],corners[2]);
        if(pos) collisions.push(pos);
        pos = line_intersect(a,b,corners[2],corners[3]);
        if(pos) collisions.push(pos);
        pos = line_intersect(a,b,corners[3],corners[0]);
        if(pos) collisions.push(pos);
        return collisions;
    };

    // returns true if the rectangle contains the position defined by the vector 'vec'
    BRect.prototype.contains_vec = function(vec){
        return ( vec.x >= this.x && vec.x <= this.mx && 
                 vec.y >= this.y && vec.y <= this.my  );
    };
    // returns true if the rectangle contains the position (x,y) 
    BRect.prototype.contains_xy = function(x,y){
        return ( x >= this.x && x <= this.mx && 
                 y >= this.y && y <= this.my  );
    };
    // returns true if the ellipse contains the position defined by the vector 'vec'
    BEllipse.prototype.contains_vec = function(v){
        v = v.mult_xy(this.hx,this.hy);
        return v.len_sq() <= 1;
    };
    // returns true if the ellipse contains the position (x,y) 
    BEllipse.prototype.contains_xy = function(x,y){
        return this.contains(new Vec2(x,y));
    };


})(window);
        

