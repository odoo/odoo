
(function(window){


    // this serves as the end of an edge when creating a link
    function EdgeEnd(pos_x,pos_y){
        this.x = pos_x;
        this.y = pos_y;

        this.get_pos = function(){
            return new Vec2(this.x,this.y);
        }
    }

    // connectors are start and end point of edge creation drags.
    function Connector(graph,node,pos_x,pos_y){
        var visible = false;
        var conn_circle = graph.r.circle(node.get_pos().x + pos_x, node.get_pos().y + pos_y,4);
        conn_circle.attr({'opacity':0, 'fill':graph.style.outline,'stroke':'none'});
        var self = this;

        this.update_pos = function(){
            conn_circle.attr({'cx':node.get_pos().x + pos_x, 'cy':node.get_pos().y + pos_y});
        }
        this.get_pos = function(){
            return new node.get_pos().add_xy(pos_x,pos_y);
        }
        function hover_in(){
            if(!visible){ return;}
            conn_circle.animate({'r':8},300,'elastic');
            if(graph.creating_edge){
                graph.target_node = node; 
                conn_circle.animate({'fill':graph.style.white,'stroke':graph.style.outline,'stroke-width':2},100,'linear');
            }
        }
        function hover_out(){
            if(!visible){ return;}
            conn_circle.animate({'r':4, 'fill':graph.style.outline, 'stroke':'none'},400,'linear');
            graph.target_node = null;
        }
        conn_circle.hover(hover_in,hover_out);


        var drag_down = function(){
            if(!visible){ return; }
            self.ox = conn_circle.attr("cx");
            self.oy = conn_circle.attr("cy");
            self.edge_start = new EdgeEnd(self.ox,self.oy);
            self.edge_end = new EdgeEnd(self.ox, self.oy);
            self.edge_tmp = new GraphEdge(graph,'',self.edge_start,self.edge_end,true);
            graph.creating_edge = true;
        }
        var drag_move = function(dx,dy){
            if(!visible){ return; }
            self.edge_end.x = self.ox + dx;
            self.edge_end.y = self.oy + dy;
            self.edge_tmp.update();
        }
        var drag_up = function(){
            if(!visible){ return; }
            graph.creating_edge = false;
            self.edge_tmp.remove();
            if(graph.target_node && graph.target_node != node){
                new GraphEdge(graph,'new edge!', node,graph.target_node);
            }
        }
        conn_circle.drag(drag_move,drag_down,drag_up);

        function show(){
            if(!visible){
                conn_circle.animate({'opacity':1}, 100, 'linear');
                visible = true;
            }
        }
        function hide(){
            if(visible){
                conn_circle.animate({'opacity':0}, 100, 'linear');
                visible = false;
            }
        }

        this.show = show;
        this.hide = hide;
    }
    
    function Graph(r,style){
        var nodes = [];  // list of all nodes in the graph
        var edges = [];  // list of all edges in the graph
        var graph = {};  // graph[n1.uid][n2.uid] -> list of all edges from n1 to n2
        var links = {}   // links[n.uid] -> list of all edges from or to n
        var uid = 1;     // all nodes and edges have an uid used to order their display when they are curved
        
        this.creating_edge = false; // true if we are dragging a new edge onto a node
        this.target_node = null;    // this holds the target node when creating an edge and hovering a connector
        this.r = r;                 // the raphael instance
        this.style  = style;        // definition of the colors, spacing, fonts, ... used by the elements

        //adds a node to the graph and sets its uid.
        this.add_node = function (n){
            nodes.push(n);
            n.uid = uid++;
        };
        //return the list of all nodes in the graph
        this.get_node_list = function(){
            return nodes;
        };
        //adds an edge to the graph and sets its uid
        this.add_edge = function (n1,n2,e){
            edges.push(e);
            e.uid = uid++;
            if(!graph[n1.uid])          graph[n1.uid] = {};
            if(!graph[n1.uid][n2.uid])  graph[n1.uid][n2.uid] = [];
            if(!links[n1.uid]) links[n1.uid] = [];
            if(!links[n2.uid]) links[n2.uid] = [];

            graph[n1.uid][n2.uid].push(e);
            links[n1.uid].push(e);
            links[n2.uid].push(e);
        };
        //return the list of edges from n1 to n2
        this.get_edge_list = function(n1,n2){
            var list = [];
            if(!graph[n1.uid]) return list;
            if(!graph[n1.uid][n2.uid]) return list;
            return graph[n1.uid][n2.uid];
        };
        //returns the list of all edge connected to n
        this.get_linked_edge_list = function(n){
            if(!links[n.uid]) return [];
            return links[n.uid];
        }
        //return a curvature index so that all edges connecting n1,n2 have different curvatures
        this.get_edge_curvature = function(n1,n2,e){
            var el_12 = this.get_edge_list(n1,n2);
            var c12   = el_12.length;
            var el_21 = this.get_edge_list(n2,n1);
            var c21   = el_21.length;
            if(c12 + c21 == 1){ // only one edge 
                return 0;
            }else{ 
                var index = 0;
                for(var i = 0; i < c12; i++){
                    if (el_12[i].uid < e.uid){
                        index++;
                    }
                }
                if(c21 == 0){   // all edges in the same direction
                    return index - (c12-1)/2.0;
                }else{
                    return index + 0.5;
                }
            }
        };
    }

    // creates a new Graph Node on Raphael document r, centered on [pos_x,pos_y], with label 'label', 
    // and of type 'circle' or 'rect', and of color 'color'
    // TODO pass graph in constructor
    function GraphNode(graph,pos_x, pos_y,label,type,color){
        var r  = graph.r;
        var sy = graph.style.node_size_y;
        var sx = graph.style.node_size_x;
        var node_fig = null;
        //var node_shadow = null;
        var self = this;
        var selected = false;
        this.update_time = 0;
        this.connectors = [];
        this.uid = 0;
        
        graph.add_node(this);

        if(type == 'circle'){
            node_fig = r.ellipse(pos_x,pos_y,sx/2,sy/2);
        }else{
            node_fig = r.rect(pos_x-sx/2,pos_y-sy/2,sx,sy);
        }
        node_fig.attr({'fill':color, 'stroke':graph.style.outline,'stroke-width':1,'cursor':'pointer'});

        var node_label = r.text(pos_x,pos_y,label);
        node_label.attr({'fill':graph.style.text,'cursor':'pointer'});

        
        // sets the center position of the node
        var set_pos = function(pos){
            if(type == 'circle'){
                node_fig.attr({'cx':pos.x,'cy':pos.y});
            }else{
                node_fig.attr({'x':pos.x-sx/2,'y':pos.y-sy/2});
            }
            node_label.attr({'x':pos.x,'y':pos.y});
            for(var i = 0; i < self.connectors.length; i++){
                self.connectors[i].update_pos();
            }
            var edges = graph.get_linked_edge_list(self);
            for(var i = 0; i < edges.length; i++){
                edges[i].update();
            }
        }
        // returns the figure used to draw the node
        var get_fig = function(){
            return node_fig;
        }
        // returns the center coordinates
        var get_pos = function(){
            if(type == 'circle'){ 
                return new Vec2(node_fig.attr('cx'), node_fig.attr('cy')); 
            }else{ 
                return new Vec2(node_fig.attr('x') + sx/2, node_fig.attr('y') + sy/2); 
            }
        }
        // return the label string
        var get_label = function(){
            return node_label.attr("text");
        }
        // sets the label string
        var set_label = function(text){
            node_label.attr({'text':text});
        }
        var get_bound = function(){
            if(type == 'circle'){
                return new BEllipse(get_pos().x,get_pos().y,sx/2,sy/2);
            }else{
                return BRect.new_centered(get_pos().x,get_pos().y,sx,sy);
            }
        }
        // selects this node and deselects all other nodes
        var set_selected = function(){
            if(!selected){
                node_fig.attr({'stroke':graph.style.selected, 'stroke-width':2});
                selected = true;
                var nodes = graph.get_node_list();
                for(var i = 0; i < nodes.length; i++){
                    if(nodes[i] != self){
                        nodes[i].set_not_selected();
                    }
                }
                for(var i = 0; i < self.connectors.length; i++){
                    self.connectors[i].show();
                }
            }
        }
        // deselect this node
        var set_not_selected = function(){
            if(selected){
                node_fig.animate({'stroke':graph.style.outline,'stroke-width':1},100,'linear');
                selected = false;
            }
            for(var i = 0; i < self.connectors.length; i++){
                self.connectors[i].hide();
            }
        }

        this.set_pos = set_pos;
        this.get_pos = get_pos;
        this.set_label = set_label;
        this.get_label = get_label;
        this.get_bound = get_bound;
        this.get_fig   = get_fig;
        this.set_selected = set_selected;
        this.set_not_selected = set_not_selected

       
        //select the node and play an animation when clicked
        var click_action = function(){
            if(type == 'circle'){
                node_fig.attr({'rx':sx/2 + 3, 'ry':sy/2+ 3});
                node_fig.animate({'rx':sx/2, 'ry':sy/2},500,'elastic');
            }else{
                var cx = get_pos().x;
                var cy = get_pos().y;
                node_fig.attr({'x':cx - (sx/2) - 3, 'y':cy - (sy/2) - 3, 'ẃidth':sx+6, 'height':sy+6});
                node_fig.animate({'x':cx - sx/2, 'y':cy - sy/2, 'ẃidth':sx, 'height':sy},500,'elastic');
            }
            set_selected();
        }
        node_fig.click(click_action);
        node_label.click(click_action);

        //move the node when dragged
        var drag_down = function(){
            this.opos = get_pos();
        }
        var drag_move = function(dx,dy){
            // we disable labels when moving for performance reasons, 
            // updating the label position is quite expensive
            // we put this here because drag_down is also called on simple clicks ... and this causes unwanted flicker
            var edges = graph.get_linked_edge_list(self);
            for(var i = 0; i < edges.length; i++){
                edges[i].label_disable();
            }
            set_pos(this.opos.add_new_xy(dx,dy));
        }
        var drag_up = function(){
            //we re-enable the 
            var edges = graph.get_linked_edge_list(self);
            for(var i = 0; i < edges.length; i++){
                edges[i].label_enable();
            }
            
        }
        node_fig.drag(drag_move,drag_down,drag_up);
        node_label.drag(drag_move,drag_down,drag_up);

        //allow the user to create edges by dragging onto the node
        function hover_in(){
            if(graph.creating_edge){
                graph.target_node = self; 
            }
        }
        function hover_out(){
            graph.target_node = null;
        }
        node_fig.hover(hover_in,hover_out);
        node_label.hover(hover_in,hover_out);

        this.connectors.push(new Connector(graph,this,-sx/2,0));
        this.connectors.push(new Connector(graph,this,sx/2,0));
        this.connectors.push(new Connector(graph,this,0,-sy/2));
        this.connectors.push(new Connector(graph,this,0,sy/2));
    }

    // creates a new edge with label 'label' from start to end. start and end must implement get_pos_*, 
    // if tmp is true, the edge is not added to the graph, used for drag edges. TODO pass graph in constructor,
    // replace tmp == false by graph == null 
    function GraphEdge(graph,label,start,end,tmp){
        var r = graph.r;
        var update_time = -1;
        var curvature = 0;  // 0 = straight, != 0 curved
        var s,e;            // positions of the start and end point of the line between start and end
        var mc;             // position of the middle of the curve (bezier control point) 
        var elfs =  graph.style.edge_label_font_size || 10 ; 
        var label_enabled = true;
        this.uid = 0;       // unique id used to order the curved edges
        var self = this;

        if(!tmp){
            graph.add_edge(start,end,this);
        }
        
        function get_label_pos(path){
            var cpos = path.getTotalLength() * 0.5;
            var cindex = Math.abs(Math.floor(curvature));
            var mod = ((cindex % 3)) * (elfs * 3.1) - (elfs * 0.5);
            var verticality = Math.abs(end.get_pos().sub_new(start.get_pos()).normalize().dot_xy(0,1));
            verticality = Math.max(verticality-0.5,0)*2;

            var lpos = path.getPointAtLength(cpos + mod * verticality);
            return new Vec2(lpos.x,lpos.y - elfs *(1-verticality));
        }
            
        //computes new start and end line coordinates
        function update_start_end_pos(){
            if(!tmp){
                curvature = graph.get_edge_curvature(start,end,self);
            }else{
                curvature = 0;
            }
            s = start.get_pos();
            e = end.get_pos();
            mc = s.lerp_new(e,0.5); //middle of the line s->e
            var se = e.sub_new(s);
            se.normalize();
            se.rotate_deg(-90);
            se.scale(curvature * graph.style.edge_spacing);
            mc.add(se);
            if(start.get_bound){
                var col = start.get_bound().collide_segment(s,mc);
                if(col.length > 0){
                    s = col[0];
                }
            }
            if(end.get_bound){
                var col = end.get_bound().collide_segment(mc,e);
                if(col.length > 0){
                    e = col[0];
                }
            }
        }
        
        function make_line(){
            return "M" + s.x + "," + s.y + "L" + e.x + "," + e.y ;
        }
        function make_curve(){
            return "M" + s.x + "," + s.y + "Q" + mc.x + "," + mc.y + " " + e.x + "," + e.y;
        }

        update_start_end_pos();
        var edge = r.path(make_curve()).attr({'stroke':graph.style.edge, 'stroke-width':2, 'arrow-end':'block-wide-long', 'cursor':'pointer'}).insertBefore(graph.get_node_list()[0].get_fig());       
        var labelpos = get_label_pos(edge);
        var edge_label = r.text(labelpos.x, labelpos.y - elfs, label).attr({'fill':graph.style.edge_label, 'cursor':'pointer', 'font-size':elfs});
        

        //since we create an edge we need to recompute the edges that have the same start and end positions as this one
        if(!tmp){
            var edges_start = graph.get_linked_edge_list(start);
            var edges_end   = graph.get_linked_edge_list(end);
            var edges = edges_start.length < edges_end.length ? edges_start : edges_end;
            for(var i = 0; i < edges.length; i ++){
                if(edges[i] != self){
                    edges[i].update();
                }
            }
        }

        function label_enable(){
            if(!label_enabled){
                label_enabled = true;
                edge_label.animate({'opacity':1},100,'linear');
                self.update();
            }
        }
        function label_disable(){
            if(label_enabled){
                label_enabled = false;
                edge_label.animate({'opacity':0},100,'linear');
            }
        }
        //update the positions 
        function update(){
            update_start_end_pos();
            edge.attr({'path':make_curve()});
            if(label_enabled){
                var labelpos = get_label_pos(edge);
                edge_label.attr({'x':labelpos.x, 'y':labelpos.y - 14});
            }
        }
        //TODO remove from graph
        function remove(){
            edge.remove();
            edge_label.remove();
        }

        this.label_enable  = label_enable;
        this.label_disable = label_disable;
        this.update = update;
        this.remove = remove;
        
    }
    // returns a new string with the same content as str, but with lines of maximum 'width' characters.
    // lines are broken on words, or into words if a word is longer than 'width'
    function wordwrap( str, width) {
        // http://james.padolsey.com/javascript/wordwrap-for-javascript/
        width = width || 32;
        var cut = true;
        var brk = '\n';
        if (!str) { return str; }
        var regex = '.{1,' +width+ '}(\\s|$)' + (cut ? '|.{' +width+ '}|.+$' : '|\\S+?(\\s|$)');
        return str.match( RegExp(regex, 'g') ).join( brk );                             
    }

    window.CuteGraph   = Graph;
    window.CuteNode    = GraphNode;
    window.CuteEdge    = GraphEdge;

    window.CuteGraph.wordwrap = wordwrap;


})(window);

/*
window.onload = function(){
    var style = {   "background"    :'url("grid.png")',
                    "edge"          :"#A0A0A0",
                    "edge_label"    :"#555",
                    "text"          :"#333",
                    "outline"       :"#000",
                    "selected"      :"#0097BE",
                    "gray"          :"#DCDCDC",
                    "white"         :"#FFF",
                    "node_size_x"   : 110,
                    "node_size_y"   : 80,
                    "edge_spacing"  : 100                 };

    var r = new Raphael(document.getElementById("canvas_container"),'100%','100%');

    var g = new CuteGraph(r,style);
    
    var n1 = new GraphNode(g,100,250,'Hello World','circle',colors.white);
    var n2 = new GraphNode(g,400,250,'Hello Planet','rect',colors.white);
    var n3 = new GraphNode(g,250,400,'Lonely Node','rect',colors.gray);
    var e1 = new GraphEdge(g,'test',n1,n2);
}*/

