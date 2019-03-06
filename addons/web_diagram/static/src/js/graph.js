
(function(window){

    // this serves as the end of an edge when creating a link
    function EdgeEnd(pos_x,pos_y){
        this.x = pos_x;
        this.y = pos_y;

        this.get_pos = function(){
            return new Vec2(this.x,this.y);
        }
    }

    // A close button, 
    // if entity_type == "node":
    //      GraphNode.destruction_callback(entity) is called where entity is a node.
    //      If it returns true the node and all connected edges are destroyed.
    // if entity_type == "edge":
    //      GraphEdge.destruction_callback(entity) is called where entity is an edge
    //      If it returns true the edge is destroyed
    // pos_x,pos_y is the relative position of the close button to the entity position (entity.get_pos())

    function CloseButton(graph, entity, entity_type, pos_x,pos_y){
        var self = this;
        var visible = false;
        var close_button_radius = graph.style.close_button_radius || 8;
        var close_circle = graph.r.circle(  entity.get_pos().x + pos_x, 
                                            entity.get_pos().y + pos_y, 
                                            close_button_radius           );
        //the outer gray circle
        close_circle.attr({ 'opacity':  0,
                            'fill':     graph.style.close_button_color || "black",
                            'cursor':   'pointer',
                            'stroke':   'none'  });
        close_circle.transform(graph.get_transform());
        graph.set_scrolling(close_circle);
        
        //the 'x' inside the circle
        var close_label = graph.r.text( entity.get_pos().x + pos_x, entity.get_pos().y + pos_y,"x");
        close_label.attr({  'fill':         graph.style.close_button_x_color || "white",
                            'font-size':    close_button_radius,
                            'cursor':       'pointer'   });
        
        close_label.transform(graph.get_transform());
        graph.set_scrolling(close_label);
        
        // the dummy_circle is used to catch events, and avoid hover in/out madness 
        // between the 'x' and the button
        var dummy_circle = graph.r.circle(  entity.get_pos().x + pos_x,
                                            entity.get_pos().y + pos_y,
                                            close_button_radius           );
        dummy_circle.attr({'opacity':1, 'fill': 'transparent', 'stroke':'none', 'cursor':'pointer'});
        dummy_circle.transform(graph.get_transform());
        graph.set_scrolling(dummy_circle);

        this.get_pos = function(){
            return entity.get_pos().add_xy(pos_x,pos_y);
        };

        this.update_pos = function(){
            var pos = self.get_pos(); 
            close_circle.attr({'cx':pos.x, 'cy':pos.y});
            dummy_circle.attr({'cx':pos.x, 'cy':pos.y});
            close_label.attr({'x':pos.x, 'y':pos.y});
        };
        
        function hover_in(){
            if(!visible){ return; }
            close_circle.animate({'r': close_button_radius * 1.5}, 300, 'elastic');
            dummy_circle.animate({'r': close_button_radius * 1.5}, 300, 'elastic');
        }
        function hover_out(){
            if(!visible){ return; }
            close_circle.animate({'r': close_button_radius},400,'linear');
            dummy_circle.animate({'r': close_button_radius},400,'linear');
        }
        dummy_circle.hover(hover_in,hover_out);
        close_circle.hover(hover_in,hover_out);
        close_label.hover(hover_in,hover_out);

        function click_action(){
            if(!visible){ return; }

            close_circle.attr({'r': close_button_radius * 2 });
            dummy_circle.attr({'r': close_button_radius * 2 });
            close_circle.animate({'r': close_button_radius }, 400, 'linear');
            dummy_circle.animate({'r': close_button_radius }, 400, 'linear');

            if(entity_type == "node"){
                Promise.resolve(GraphNode.destruction_callback(entity)).then(function () {
                    entity.remove();
                });
            }else if(entity_type == "edge"){
                Promise.resolve(GraphEdge.destruction_callback(entity)).then(function () {
                    entity.remove();
                });
            }
        }
        dummy_circle.click(click_action);
        close_circle.click(click_action);
        close_label.click(click_action);

        this.show = function(){
            if(!visible){
                close_circle.animate({'opacity':1}, 100, 'linear');
                close_label.animate({'opacity':1}, 100, 'linear');
                visible = true;
            }
        }
        this.hide = function(){
            if(visible){
                close_circle.animate({'opacity':0}, 100, 'linear');
                close_label.animate({'opacity':0}, 100, 'linear');
                visible = false;
            }
        }
        //destroy this object and remove it from the graph
        this.remove = function(){
            if(visible){
                visible = false;
                close_circle.animate({'opacity':0}, 100, 'linear');
                close_label.animate({'opacity':0}, 100, 'linear',self.remove);
            }else{
                close_circle.remove();
                close_label.remove();
                dummy_circle.remove();
            }
        }
    }

    // connectors are start and end point of edge creation drags.
    function Connector(graph,node,pos_x,pos_y){
        var visible = false;
        var conn_circle = graph.r.circle(node.get_pos().x + pos_x, node.get_pos().y + pos_y,4);
        conn_circle.attr({  'opacity':  0, 
                            'fill':     graph.style.node_outline_color,
                            'stroke':   'none' });
        conn_circle.transform(graph.get_transform());
        graph.set_scrolling(conn_circle);

        var self = this;

        this.update_pos = function(){
            conn_circle.attr({'cx':node.get_pos().x + pos_x, 'cy':node.get_pos().y + pos_y});
        };
        this.get_pos = function(){
            return new node.get_pos().add_xy(pos_x,pos_y);
        };
        this.remove = function(){
            conn_circle.remove();
        }
        function hover_in(){
            if(!visible){ return;}
            conn_circle.animate({'r':8},300,'elastic');
            if(graph.creating_edge){
                graph.target_node = node; 
                conn_circle.animate({   'fill':         graph.style.connector_active_color,
                                        'stroke':       graph.style.node_outline_color,
                                        'stroke-width': graph.style.node_selected_width,
                                    },100,'linear');
            }
        }
        function hover_out(){
            if(!visible){ return;}
            conn_circle.animate({   'r':graph.style.connector_radius, 
                                    'fill':graph.style.node_outline_color, 
                                    'stroke':'none'},400,'linear');
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
        };
        var drag_move = function(dx,dy){
            if(!visible){ return; }
            self.edge_end.x = self.ox + dx;
            self.edge_end.y = self.oy + dy;
            self.edge_tmp.update();
        };
        var drag_up = function(){
            if(!visible){ return; }
            graph.creating_edge = false;
            self.edge_tmp.remove();
            if(graph.target_node){  
                var edge_prop = GraphEdge.creation_callback(node,graph.target_node);
                if(edge_prop){
                    var new_edge = new GraphEdge(graph,edge_prop.label, node,graph.target_node);
                    GraphEdge.new_edge_callback(new_edge);
                }
            }
        };
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
    
    //Creates a new graph on raphael document r.
    //style is a dictionary containing the style definitions
    //viewport (optional) is the dom element representing the viewport of the graph. It is used
    //to prevent scrolling to scroll the graph outside the viewport.

    function Graph(r,style,viewport){
        var self = this;
        var nodes = [];  // list of all nodes in the graph
        var edges = [];  // list of all edges in the graph
        var graph = {};  // graph[n1.uid][n2.uid] -> list of all edges from n1 to n2
        var links = {};  // links[n.uid] -> list of all edges from or to n
        var uid = 1;     // all nodes and edges have an uid used to order their display when they are curved
        var selected_entity = null; //the selected entity (node or edge) 
        
        self.creating_edge = false; // true if we are dragging a new edge onto a node
        self.target_node = null;    // this holds the target node when creating an edge and hovering a connector
        self.r = r;                 // the raphael instance
        self.style  = style;        // definition of the colors, spacing, fonts, ... used by the elements
        var tr_x = 0, tr_y = 0;         // global translation coordinate

        var background = r.rect(0,0,'100%','100%').attr({'fill':'white', 'stroke':'none', 'opacity':0, 'cursor':'move'});
        
        // return the global transform of the scene
        this.get_transform = function(){
            return "T"+tr_x+","+tr_y
        };

        
        // translate every element of the graph except the background. 
        // elements inserted in the graph after a translate_all() must manually apply transformation 
        // via get_transform() 
        var translate_all = function(dx,dy){
            tr_x += dx;
            tr_y += dy;
            var tstr = self.get_transform();
            
            r.forEach(function(el){
                if(el != background){
                    el.transform(tstr);
                }
            });
        };
        //returns {minx, miny, maxx, maxy}, the translated bounds containing all nodes
        var get_bounds = function(){
            var minx = Number.MAX_VALUE;
            var miny = Number.MAX_VALUE;
            var maxx = Number.MIN_VALUE;
            var maxy = Number.MIN_VALUE;
            
            for(var i = 0; i < nodes.length; i++){
                var pos = nodes[i].get_pos();
                minx = Math.min(minx,pos.x);
                miny = Math.min(miny,pos.y);
                maxx = Math.max(maxx,pos.x);
                maxy = Math.max(maxy,pos.y);
            }

            minx = minx - style.node_size_x / 2 + tr_x;
            miny = miny - style.node_size_y / 2 + tr_y;
            maxx = maxx + style.node_size_x / 2 + tr_x;
            maxy = maxy + style.node_size_y / 2 + tr_y;

            return { minx:minx, miny:miny, maxx:maxx, maxy:maxy };
        
        };
        // returns false if the translation dx,dy of the viewport 
        // hides the graph (with optional margin)
        var translation_respects_viewport = function(dx,dy,margin){
            if(!viewport){
                return true;
            }
            margin = margin || 0;
            var b = get_bounds();
            var width = viewport.offsetWidth; 
            var height = viewport.offsetHeight;
            
            if( ( dy < 0 && b.maxy + dy < margin )   ||
                ( dy > 0 && b.miny + dy > height - margin ) ||
                ( dx < 0 && b.maxx + dx < margin ) ||
                ( dx > 0 && b.minx + dx > width - margin ) ){
                return false;
            }

            return true;
        }
        //Adds a mousewheel event callback to raph_element that scrolls the viewport
        this.set_scrolling = function(raph_element){
            $(raph_element.node).bind('mousewheel',function(event,delta){
                var dy = delta * 20;
                if( translation_respects_viewport(0,dy, style.viewport_margin) ){
                    translate_all(0,dy);
                }
            });
        };

        var px, py;
        // Graph translation when background is dragged
        var bg_drag_down = function(){
            px = py = 0;
        };
        var bg_drag_move = function(x,y){
            var dx = x - px;
            var dy = y - py;
            px = x;
            py = y;
            if( translation_respects_viewport(dx,dy, style.viewport_margin) ){
                translate_all(dx,dy);
            }
        };
        var bg_drag_up   = function(){};
        background.drag( bg_drag_move, bg_drag_down, bg_drag_up);
        
        this.set_scrolling(background);

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
            if(n1 != n2){
                links[n2.uid].push(e);
            }
        };

        //removes an edge from the graph
        this.remove_edge = function(edge){
            edges = _.without(edges,edge);
            var n1 = edge.get_start();
            var n2 = edge.get_end();
            links[n1.uid] = _.without(links[n1.uid],edge);
            links[n2.uid] = _.without(links[n2.uid],edge);
            graph[n1.uid][n2.uid] = _.without(graph[n1.uid][n2.uid],edge);
            if ( selected_entity == edge ){
                selected_entity = null;
            }
        };
        //removes a node and all connected edges from the graph
        this.remove_node = function(node){
            var linked_edges = self.get_linked_edge_list(node);
            for(var i = 0; i < linked_edges.length; i++){
                linked_edges[i].remove();
            }
            nodes = _.without(nodes,node);

            if ( selected_entity == node ){
                selected_entity = null;
            }
        }


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
        };
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
        

        // Returns the angle in degrees of the edge loop. We do not support more than 8 loops on one node
        this.get_loop_angle = function(n,e){
            var loop_list = this.get_edge_list(n,n);

            var slots = []; // the 8 angles where we can put the loops 
            for(var angle = 0; angle < 360; angle += 45){
                slots.push(Vec2.new_polar_deg(1,angle));
            }
            
            //we assign to each slot a score. The higher the score, the closer it is to other edges.
            var links = this.get_linked_edge_list(n);
            for(var i = 0; i < links.length; i++){
                var edge = links[i];
                if(!edge.is_loop || edge.is_loop()){
                    continue;
                }
                var end = edge.get_end();
                if (end == n){
                    end = edge.get_start();
                }
                var dir = end.get_pos().sub(n.get_pos()).normalize();
                for(var s = 0; s < slots.length; s++){
                    var score = slots[s].dot(dir);
                    if(score < 0){
                        score = -0.2*Math.pow(score,2);
                    }else{
                        score = Math.pow(score,2);
                    }
                    if(!slots[s].score){
                        slots[s].score = score;
                    }else{
                        slots[s].score += score;
                    }
                }
            }
            //we want the loops with lower uid to get the slots with the lower score
            slots.sort(function(a,b){ return a.score < b.score ? -1: 1; });
            
            var index = 0;
            for(var i = 0; i < links.length; i++){
                var edge = links[i];
                if(!edge.is_loop || !edge.is_loop()){
                    continue;
                }
                if(edge.uid < e.uid){
                    index++;
                }
            }
            index %= slots.length;
            
            return slots[index].angle_deg();
        }

        //selects a node or an edge and deselects everything else
        this.select = function(entity){
            if(selected_entity){
                if(selected_entity == entity){
                    return;
                }else{
                    if(selected_entity.set_not_selected){
                        selected_entity.set_not_selected();
                    }
                    selected_entity = null;
                }
            }
            selected_entity = entity;
            if(entity && entity.set_selected){
                entity.set_selected();
            }
        };
    }

    // creates a new Graph Node on Raphael document r, centered on [pos_x,pos_y], with label 'label', 
    // and of type 'circle' or 'rect', and of color 'color'
    function GraphNode(graph,pos_x, pos_y,label,type,color){
        var self = this;
        var r  = graph.r;
        var sy = graph.style.node_size_y;
        var sx = graph.style.node_size_x;
        var node_fig = null;
        var selected = false;
        this.connectors = [];
        this.close_button = null;
        this.uid = 0;
        
        graph.add_node(this);

        if(type == 'circle'){
            node_fig = r.ellipse(pos_x,pos_y,sx/2,sy/2);
        }else{
            node_fig = r.rect(pos_x-sx/2,pos_y-sy/2,sx,sy);
        }
        node_fig.attr({ 'fill':         color, 
                        'stroke':       graph.style.node_outline_color,
                        'stroke-width': graph.style.node_outline_width,
                        'cursor':'pointer'  });
        node_fig.transform(graph.get_transform());
        graph.set_scrolling(node_fig);

        var node_label = r.text(pos_x,pos_y,label);
        node_label.attr({   'fill':         graph.style.node_label_color,
                            'font-size':    graph.style.node_label_font_size,
                            'cursor':       'pointer'   });
        node_label.transform(graph.get_transform());
        graph.set_scrolling(node_label);

        // redraws all edges linked to this node 
        var update_linked_edges = function(){
            var edges = graph.get_linked_edge_list(self);
            for(var i = 0; i < edges.length; i++){
                edges[i].update();
            }
        };

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
            if(self.close_button){
                self.close_button.update_pos();
            }
            update_linked_edges();
        };
        // returns the figure used to draw the node
        var get_fig = function(){
            return node_fig;
        };
        // returns the center coordinates
        var get_pos = function(){
            if(type == 'circle'){ 
                return new Vec2(node_fig.attr('cx'), node_fig.attr('cy')); 
            }else{ 
                return new Vec2(node_fig.attr('x') + sx/2, node_fig.attr('y') + sy/2); 
            }
        };
        // return the label string
        var get_label = function(){
            return node_label.attr("text");
        };
        // sets the label string
        var set_label = function(text){
            node_label.attr({'text':text});
        };
        var get_bound = function(){
            if(type == 'circle'){
                return new BEllipse(get_pos().x,get_pos().y,sx/2,sy/2);
            }else{
                return BRect.new_centered(get_pos().x,get_pos().y,sx,sy);
            }
        };
        // selects this node and deselects all other nodes
        var set_selected = function(){
            if(!selected){
                selected = true;
                node_fig.attr({ 'stroke':       graph.style.node_selected_color, 
                                'stroke-width': graph.style.node_selected_width });
                if(!self.close_button){
                    self.close_button = new CloseButton(graph,self, "node" ,sx/2 , - sy/2);
                    self.close_button.show();
                }
                for(var i = 0; i < self.connectors.length; i++){
                    self.connectors[i].show();
                }
            }
        };
        // deselect this node
        var set_not_selected = function(){
            if(selected){
                node_fig.animate({  'stroke':       graph.style.node_outline_color,
                                    'stroke-width': graph.style.node_outline_width },
                                    100,'linear');
                if(self.close_button){
                    self.close_button.remove();
                    self.close_button = null;
                }
                selected = false;
            }
            for(var i = 0; i < self.connectors.length; i++){
                self.connectors[i].hide();
            }
        };
        var remove = function(){
            if(self.close_button){
                self.close_button.remove();
            }
            for(var i = 0; i < self.connectors.length; i++){
                self.connectors[i].remove();
            }
            graph.remove_node(self);
            node_fig.remove();
            node_label.remove();
        }


        this.set_pos = set_pos;
        this.get_pos = get_pos;
        this.set_label = set_label;
        this.get_label = get_label;
        this.get_bound = get_bound;
        this.get_fig   = get_fig;
        this.set_selected = set_selected;
        this.set_not_selected = set_not_selected;
        this.update_linked_edges = update_linked_edges;
        this.remove = remove;

       
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
            graph.select(self);
        };
        node_fig.click(click_action);
        node_label.click(click_action);

        //move the node when dragged
        var drag_down = function(){
            this.opos = get_pos();
        };
        var drag_move = function(dx,dy){
            // we disable labels when moving for performance reasons, 
            // updating the label position is quite expensive
            // we put this here because drag_down is also called on simple clicks ... and this causes unwanted flicker
            var edges = graph.get_linked_edge_list(self);
            for(var i = 0; i < edges.length; i++){
                edges[i].label_disable();
            }
            if(self.close_button){
                self.close_button.hide();
            }
            set_pos(this.opos.add_xy(dx,dy));
        };
        var drag_up = function(){
            //we re-enable the 
            var edges = graph.get_linked_edge_list(self);
            for(var i = 0; i < edges.length; i++){
                edges[i].label_enable();
            }
            if(self.close_button){
                self.close_button.show();
            }
        };
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

        function double_click(){
            GraphNode.double_click_callback(self);
        }
        node_fig.dblclick(double_click);
        node_label.dblclick(double_click);

        this.connectors.push(new Connector(graph,this,-sx/2,0));
        this.connectors.push(new Connector(graph,this,sx/2,0));
        this.connectors.push(new Connector(graph,this,0,-sy/2));
        this.connectors.push(new Connector(graph,this,0,sy/2));

        this.close_button = new CloseButton(graph,this,"node",sx/2 , - sy/2 );
    }

    GraphNode.double_click_callback = function(node){
        console.log("double click from node:",node);
    };

    // this is the default node destruction callback. It is called before the node is removed from the graph
    // and before the connected edges are destroyed 
    GraphNode.destruction_callback = function(node){ return true; };

    // creates a new edge with label 'label' from start to end. start and end must implement get_pos_*, 
    // if tmp is true, the edge is not added to the graph, used for drag edges. 
    // replace tmp == false by graph == null 
    function GraphEdge(graph,label,start,end,tmp){
        var self = this;
        var r = graph.r;
        var curvature = 0;  // 0 = straight, != 0 curved
        var s,e;            // positions of the start and end point of the line between start and end
        var mc;             // position of the middle of the curve (bezier control point) 
        var mc1,mc2;        // control points of the cubic bezier for the loop edges
        var elfs =  graph.style.edge_label_font_size || 10 ; 
        var label_enabled = true;
        this.uid = 0;       // unique id used to order the curved edges
        var edge_path = ""; // svg definition of the edge vector path
        var selected = false;

        if(!tmp){
            graph.add_edge(start,end,this);
        }
        
        //Return the position of the label
        function get_label_pos(path){
            var cpos = path.getTotalLength() * 0.5;
            var cindex = Math.abs(Math.floor(curvature));
            var mod = ((cindex % 3)) * (elfs * 3.1) - (elfs * 0.5);
            var verticality = Math.abs(end.get_pos().sub(start.get_pos()).normalize().dot_xy(0,1));
            verticality = Math.max(verticality-0.5,0)*2;

            var lpos = path.getPointAtLength(cpos + mod * verticality);
            return new Vec2(lpos.x,lpos.y - elfs *(1-verticality));
        }
        
        //used by close_button
        this.get_pos = function(){
            if(!edge){
                return start.get_pos().lerp(end.get_pos(),0.5);
            }
            return get_label_pos(edge);
            /*  
            var bbox = edge_label.getBBox(); Does not work... :(
            return new Vec2(bbox.x + bbox.width, bbox.y);*/
        }

        //Straight line from s to e
        function make_line(){
            return "M" + s.x + "," + s.y + "L" + e.x + "," + e.y ;
        }
        //Curved line from s to e by mc
        function make_curve(){
            return "M" + s.x + "," + s.y + "Q" + mc.x + "," + mc.y + " " + e.x + "," + e.y;
        }
        //Curved line from s to e by mc1 mc2
        function make_loop(){
            return "M" + s.x + " " + s.y + 
                   "C" + mc1.x + " " + mc1.y + " " + mc2.x + " " + mc2.y + " " + e.x + " " + e.y;
        }
            
        //computes new start and end line coordinates
        function update_curve(){
            if(start != end){
                if(!tmp){
                    curvature = graph.get_edge_curvature(start,end,self);
                }else{
                    curvature = 0;
                }
                s = start.get_pos();
                e = end.get_pos();
                
                mc = s.lerp(e,0.5); //middle of the line s->e
                var se = e.sub(s);
                se = se.normalize();
                se = se.rotate_deg(-90);
                se = se.scale(curvature * graph.style.edge_spacing);
                mc = mc.add(se);

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
                
                if(curvature != 0){
                    edge_path = make_curve();
                }else{
                    edge_path = make_line();
                }
            }else{ // start == end
                var rad = graph.style.edge_loop_radius || 100;
                s = start.get_pos();
                e = end.get_pos();

                var r = Vec2.new_polar_deg(rad,graph.get_loop_angle(start,self));
                mc = s.add(r);
                var p = r.rotate_deg(90);
                mc1 = mc.add(p.set_len(rad*0.5));
                mc2 = mc.add(p.set_len(-rad*0.5));
                
                if(start.get_bound){
                    var col = start.get_bound().collide_segment(s,mc1);
                    if(col.length > 0){
                        s = col[0];
                    }
                    var col = start.get_bound().collide_segment(e,mc2);
                    if(col.length > 0){
                        e = col[0];
                    }
                }
                edge_path = make_loop();
            }
        }
        
        update_curve();
        var edge = r.path(edge_path).attr({ 'stroke':       graph.style.edge_color, 
                                            'stroke-width': graph.style.edge_width, 
                                            'arrow-end':    'block-wide-long', 
                                            'cursor':'pointer'  }).insertBefore(graph.get_node_list()[0].get_fig());       
        var labelpos = get_label_pos(edge);
        var edge_label = r.text(labelpos.x, labelpos.y - elfs, label).attr({
            'fill':         graph.style.edge_label_color, 
            'cursor':       'pointer', 
            'font-size':    elfs    });

        edge.transform(graph.get_transform());
        graph.set_scrolling(edge);

        edge_label.transform(graph.get_transform());
        graph.set_scrolling(edge_label);
        

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
                if(self.close_button){
                    self.close_button.show();
                }
                self.update();
            }
        }
        function label_disable(){
            if(label_enabled){
                label_enabled = false;
                edge_label.animate({'opacity':0},100,'linear');
                if(self.close_button){
                    self.close_button.hide();
                }
            }
        }
        //update the positions 
        function update(){
            update_curve();
            edge.attr({'path':edge_path});
            if(label_enabled){
                var labelpos = get_label_pos(edge);
                edge_label.attr({'x':labelpos.x, 'y':labelpos.y - 14});
            }
        }
        // removes the edge from the scene, disconnects it from linked        
        // nodes, destroy its drawable elements.
        function remove(){
            edge.remove();
            edge_label.remove();
            if(!tmp){
                graph.remove_edge(self);
            }
            if(start.update_linked_edges){
                start.update_linked_edges();
            }
            if(start != end && end.update_linked_edges){
                end.update_linked_edges();
            }
            if(self.close_button){
                self.close_button.remove();
            }
        }

        this.set_selected = function(){
            if(!selected){
                selected = true;
                edge.attr({ 'stroke': graph.style.node_selected_color, 
                            'stroke-width': graph.style.node_selected_width });
                edge_label.attr({ 'fill': graph.style.node_selected_color });
                if(!self.close_button){
                    self.close_button = new CloseButton(graph,self,"edge",0,30);
                    self.close_button.show();
                }
            }
        };

        this.set_not_selected = function(){
            if(selected){
                selected = false;
                edge.animate({  'stroke':       graph.style.edge_color,
                                'stroke-width': graph.style.edge_width }, 100,'linear');
                edge_label.animate({ 'fill':    graph.style.edge_label_color}, 100, 'linear');
                if(self.close_button){
                    self.close_button.remove();
                    self.close_button = null;
                }
            }
        };
        function click_action(){
            graph.select(self);
        }
        edge.click(click_action);
        edge_label.click(click_action);

        function double_click_action(){
            GraphEdge.double_click_callback(self);
        }

        edge.dblclick(double_click_action);
        edge_label.dblclick(double_click_action);


        this.label_enable  = label_enable;
        this.label_disable = label_disable;
        this.update = update;
        this.remove = remove;
        this.is_loop = function(){ return start == end; };
        this.get_start = function(){ return start; };
        this.get_end   = function(){ return end; };
    }

    GraphEdge.double_click_callback = function(edge){
        console.log("double click from edge:",edge);
    };

    // this is the default edge creation callback. It is called before an edge is created
    // It returns an object containing the properties of the edge.
    // If it returns null, the edge is not created.
    GraphEdge.creation_callback = function(start,end){
        var edge_prop = {};
        edge_prop.label = 'new edge!';
        return edge_prop;
    };
    // This is is called after a new edge is created, with the new edge
    // as parameter
    GraphEdge.new_edge_callback = function(new_edge){};

    // this is the default edge destruction callback. It is called before 
    // an edge is removed from the graph.
    GraphEdge.destruction_callback = function(edge){ return true; };

    

    // returns a new string with the same content as str, but with lines of maximum 'width' characters.
    // lines are broken on words, or into words if a word is longer than 'width'
    function wordwrap( str, width) {
        // http://james.padolsey.com/javascript/wordwrap-for-javascript/
        width = width || 32;
        var cut = true;
        var brk = '\n';
        if (!str) { return str; }
        var regex = '.{1,' +width+ '}(\\s|$)' + (cut ? '|.{' +width+ '}|.+$' : '|\\S+?(\\s|$)');
        return str.match(new RegExp(regex, 'g') ).join( brk );
    }

    window.CuteGraph   = Graph;
    window.CuteNode    = GraphNode;
    window.CuteEdge    = GraphEdge;

    window.CuteGraph.wordwrap = wordwrap;


})(window);

