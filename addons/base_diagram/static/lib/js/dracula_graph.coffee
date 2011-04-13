###
 *  Dracula Graph Layout and Drawing Framework 0.0.3alpha
 *  (c) 2010 Philipp Strathausen <strathausen@gmail.com>, http://strathausen.eu
 *  
 *  Contributions by:
 *  Branched by Jake Stothard <stothardj@gmail.com>.
 *
 *  based on the Graph JavaScript framework, version 0.0.1
 *  (c) 2006 Aslak Hellesoy <aslak.hellesoy@gmail.com>
 *  (c) 2006 Dave Hoover <dave.hoover@gmail.com>
 *
 *  Ported from Graph::Layouter::Spring in
 *    http://search.cpan.org/~pasky/Graph-Layderer-0.02/
 *  The algorithm is based on a spring-style layouter of a Java-based social
 *  network tracker PieSpy written by Paul Mutton E<lt>paul@jibble.orgE<gt>.
 *
 *  This code is freely distributable under the terms of an MIT-style license.
 *  For details, see the Graph web site: http://dev.buildpatternd.com/trac
 *
 *  Links:
 *
 *  Graph Dracula JavaScript Framework:
 *      http://graphdracula.net
 *
 *  Demo of the original applet:
 *      http://redsquirrel.com/dave/work/webdep/
 *
 *  Mirrored original source code at snipplr:
 *      http://snipplr.com/view/1950/graph-javascript-framework-version-001/
 *
 *  Original usage example:
 *      http://ajaxian.com/archives/new-javascriptcanvas-graph-library
 *
###


###
    Edge Factory
###
AbstractEdge = ->

AbstractEdge.prototype =
    hide: ->
        @connection.fg.hide()
        @connection.bg && @bg.connection.hide()

EdgeFactory = ->
    @template = new AbstractEdge()
    @template.style = new Object()
    @template.style.directed = false
    @template.weight = 1

EdgeFactory.prototype =
    build: (source, target) ->
        e = jQuery.extend true, {}, @template
        e.source = source
        e.target = target
        e

###
    Graph
###
Graph = ->
    @nodes = {}
    @edges = []
    @snapshots = [] # previous graph states TODO to be implemented
    @edgeFactory = new EdgeFactory()

Graph.prototype =
###
    add a node
    @id          the node's ID (string or number)
    @content     (optional, dictionary) can contain any information that is
                 being interpreted by the layout algorithm or the graph
                 representation
###
    addNode: (id, content) ->
        # testing if node is already existing in the graph
        if @nodes[id] == undefined
            @nodes[id] = new Graph.Node id, content
        @nodes[id]

    addEdge: (source, target, style) ->
        s = @addNode source
        t = @addNode target
        var edge = @edgeFactory.build s, t
        jQuery.extend edge.style, style
        s.edges.push edge
        @edges.push edge
        # NOTE: Even directed edges are added to both nodes.
        t.edges.push edge

    # TODO to be implemented
    # Preserve a copy of the graph state (nodes, positions, ...)
    # @comment     a comment describing the state
    snapShot: (comment) ->
        ###/* FIXME
        var graph = new Graph()
        graph.nodes = jQuery.extend(true, {}, @nodes)
        graph.edges = jQuery.extend(true, {}, @edges)
        @snapshots.push({comment: comment, graph: graph})
        */
        ###

    removeNode: (id) ->
        delete @nodes[id]
        for i = 0; i < @edges.length; i++
            if @edges[i].source.id == id || @edges[i].target.id == id
                @edges.splice(i, 1)
                i--

/*
 * Node
 */
Graph.Node = (id, node) ->
    node = node || {}
    node.id = id
    node.edges = []
    node.hide = ->
        @hidden = true
        @shape && @shape.hide() # FIXME this is representation specific code and should be elsewhere */
        for(i in @edges)
            (@edges[i].source.id == id || @edges[i].target == id) && @edges[i].hide && @edges[i].hide()

    node.show = ->
        @hidden = false
        @shape && @shape.show()
        for(i in @edges)
            (@edges[i].source.id == id || @edges[i].target == id) && @edges[i].show && @edges[i].show()

    node

Graph.Node.prototype = { }

###
    Renderer base class
###
Graph.Renderer = { }

###
    Renderer implementation using RaphaelJS
###
Graph.Renderer.Raphael = (element, graph, width, height) ->
    @width = width || 400
    @height = height || 400
    var selfRef = this
    @r = Raphael element, @width, @height
    @radius = 40 # max dimension of a node
    @graph = graph
    @mouse_in = false

    # TODO default node rendering
    if(!@graph.render) {
        @graph.render = ->
            return
        }
    }
    
    /*
     * Dragging
     */
    @isDrag = false
    @dragger = (e) ->
        @dx = e.clientX
        @dy = e.clientY
        selfRef.isDrag = this
        @set && @set.animate "fill-opacity": .1, 200 && @set.toFront()
        e.preventDefault && e.preventDefault()

    document.onmousemove =  (e) {
        e = e || window.event
        if (selfRef.isDrag) {
            var bBox = selfRef.isDrag.set.getBBox()
            // TODO round the coordinates here (eg. for proper image representation)
            var newX = e.clientX - selfRef.isDrag.dx + (bBox.x + bBox.width / 2)
            var newY = e.clientY - selfRef.isDrag.dy + (bBox.y + bBox.height / 2)
            /* prevent shapes from being dragged out of the canvas */
            var clientX = e.clientX - (newX < 20 ? newX - 20 : newX > selfRef.width - 20 ? newX - selfRef.width + 20 : 0)
            var clientY = e.clientY - (newY < 20 ? newY - 20 : newY > selfRef.height - 20 ? newY - selfRef.height + 20 : 0)
            selfRef.isDrag.set.translate(clientX - Math.round(selfRef.isDrag.dx), clientY - Math.round(selfRef.isDrag.dy))
            //            console.log(clientX - Math.round(selfRef.isDrag.dx), clientY - Math.round(selfRef.isDrag.dy))
            for (var i in selfRef.graph.edges) {
                selfRef.graph.edges[i].connection && selfRef.graph.edges[i].connection.draw()
            }
            //selfRef.r.safari()
            selfRef.isDrag.dx = clientX
            selfRef.isDrag.dy = clientY
        }
    }
    document.onmouseup =  ->
        selfRef.isDrag && selfRef.isDrag.set.animate({"fill-opacity": .6}, 500)
        selfRef.isDrag = false
    }
    @draw()
}
Graph.Renderer.Raphael.prototype = {
    translate: (point) {
        return [
            (point[0] - @graph.layoutMinX) * @factorX + @radius,
            (point[1] - @graph.layoutMinY) * @factorY + @radius
        ]
    },

    rotate: (point, length, angle) {
        var dx = length * Math.cos(angle)
        var dy = length * Math.sin(angle)
        return [point[0]+dx, point[1]+dy]
    },

    draw: ->
        @factorX = (@width - 2 * @radius) / (@graph.layoutMaxX - @graph.layoutMinX)
        @factorY = (@height - 2 * @radius) / (@graph.layoutMaxY - @graph.layoutMinY)
        for (i in @graph.nodes) {
            @drawNode(@graph.nodes[i])
        }
        for (var i = 0; i < @graph.edges.length; i++) {
            @drawEdge(@graph.edges[i])
        }
    },

    drawNode: (node) {
        var point = @translate([node.layoutPosX, node.layoutPosY])
        node.point = point

        /* if node has already been drawn, move the nodes */
        if(node.shape) {
            var oBBox = node.shape.getBBox()
            var opoint = { x: oBBox.x + oBBox.width / 2, y: oBBox.y + oBBox.height / 2}
            node.shape.translate(Math.round(point[0] - opoint.x), Math.round(point[1] - opoint.y))
            @r.safari()
            return node
        }/* else, draw new nodes */

        var shape

        /* if a node renderer  is provided by the user, then use it 
           or the default render  instead */
        if(!node.render) {
            node.render = (r, node) {
                /* the default node drawing */
                var color = Raphael.getColor()
                var ellipse = r.ellipse(0, 0, 30, 20).attr({fill: color, stroke: color, "stroke-width": 2})
                /* set DOM node ID */
                ellipse.node.id = node.label || node.id
                shape = r.set().
                    push(ellipse).
                    push(r.text(0, 30, node.label || node.id))
                return shape
            }
        }
        /* or check for an ajax representation of the nodes */
        if(node.shapes) {
            // TODO ajax representation evaluation
        }

        shape = node.render(@r, node).hide()

        shape.attr({"fill-opacity": .6})
        /* re-reference to the node an element belongs to, needed for dragging all elements of a node */
        shape.items.forEach((item){ item.set = shape; item.node.style.cursor = "move"; })
        shape.mousedown(@dragger)

        var box = shape.getBBox()
        shape.translate(Math.round(point[0]-(box.x+box.width/2)),Math.round(point[1]-(box.y+box.height/2)))
        //console.log(box,point)
        node.hidden || shape.show()
        node.shape = shape
    },
    drawEdge: (edge) {
        /* if this edge already exists the other way around and is undirected */
        if(edge.backedge)
            return
        if(edge.source.hidden || edge.target.hidden) {
            edge.connection && edge.connection.fg.hide() | edge.connection.bg && edge.connection.bg.hide()
            return
        }
        /* if edge already has been drawn, only refresh the edge */
        if(!edge.connection) {
            edge.style && edge.style.callback && edge.style.callback(edge); // TODO move this somewhere else
            edge.connection = @r.connection(edge.source.shape, edge.target.shape, edge.style)
            return
        }
        //FIXME showing doesn't work well
        edge.connection.fg.show()
        edge.connection.bg && edge.connection.bg.show()
        edge.connection.draw()
    }
}
Graph.Layout = {}
Graph.Layout.Spring = (graph) {
    @graph = graph
    @iterations = 500
    @maxRepulsiveForceDistance = 6
    @k = 2
    @c = 0.01
    @maxVertexMovement = 0.5
    @layout()
}
Graph.Layout.Spring.prototype = {
    layout: ->
        @layoutPrepare()
        for (var i = 0; i < @iterations; i++) {
            @layoutIteration()
        }
        @layoutCalcBounds()
    },
    
    layoutPrepare: ->
        for (i in @graph.nodes) {
            var node = @graph.nodes[i]
            node.layoutPosX = 0
            node.layoutPosY = 0
            node.layoutForceX = 0
            node.layoutForceY = 0
        }
        
    },
    
    layoutCalcBounds: ->
        var minx = Infinity, maxx = -Infinity, miny = Infinity, maxy = -Infinity

        for (i in @graph.nodes) {
            var x = @graph.nodes[i].layoutPosX
            var y = @graph.nodes[i].layoutPosY
            
            if(x > maxx) maxx = x
            if(x < minx) minx = x
            if(y > maxy) maxy = y
            if(y < miny) miny = y
        }

        @graph.layoutMinX = minx
        @graph.layoutMaxX = maxx
        @graph.layoutMinY = miny
        @graph.layoutMaxY = maxy
    },
    
    layoutIteration: ->
        // Forces on nodes due to node-node repulsions

        var prev = new Array()
        for(var c in @graph.nodes) {
            var node1 = @graph.nodes[c]
            for (var d in prev) {
                var node2 = @graph.nodes[prev[d]]
                @layoutRepulsive(node1, node2)
                
            }
            prev.push(c)
        }
        
        // Forces on nodes due to edge attractions
        for (var i = 0; i < @graph.edges.length; i++) {
            var edge = @graph.edges[i]
            @layoutAttractive(edge);             
        }
        
        // Move by the given force
        for (i in @graph.nodes) {
            var node = @graph.nodes[i]
            var xmove = @c * node.layoutForceX
            var ymove = @c * node.layoutForceY

            var max = @maxVertexMovement
            if(xmove > max) xmove = max
            if(xmove < -max) xmove = -max
            if(ymove > max) ymove = max
            if(ymove < -max) ymove = -max
            
            node.layoutPosX += xmove
            node.layoutPosY += ymove
            node.layoutForceX = 0
            node.layoutForceY = 0
        }
    },

    layoutRepulsive: (node1, node2) {
        var dx = node2.layoutPosX - node1.layoutPosX
        var dy = node2.layoutPosY - node1.layoutPosY
        var d2 = dx * dx + dy * dy
        if(d2 < 0.01) {
            dx = 0.1 * Math.random() + 0.1
            dy = 0.1 * Math.random() + 0.1
            var d2 = dx * dx + dy * dy
        }
        var d = Math.sqrt(d2)
        if(d < @maxRepulsiveForceDistance) {
            var repulsiveForce = @k * @k / d
            node2.layoutForceX += repulsiveForce * dx / d
            node2.layoutForceY += repulsiveForce * dy / d
            node1.layoutForceX -= repulsiveForce * dx / d
            node1.layoutForceY -= repulsiveForce * dy / d
        }
    },

    layoutAttractive: (edge) {
        var node1 = edge.source
        var node2 = edge.target
        
        var dx = node2.layoutPosX - node1.layoutPosX
        var dy = node2.layoutPosY - node1.layoutPosY
        var d2 = dx * dx + dy * dy
        if(d2 < 0.01) {
            dx = 0.1 * Math.random() + 0.1
            dy = 0.1 * Math.random() + 0.1
            var d2 = dx * dx + dy * dy
        }
        var d = Math.sqrt(d2)
        if(d > @maxRepulsiveForceDistance) {
            d = @maxRepulsiveForceDistance
            d2 = d * d
        }
        var attractiveForce = (d2 - @k * @k) / @k
        if(edge.attraction == undefined) edge.attraction = 1
        attractiveForce *= Math.log(edge.attraction) * 0.5 + 1
        
        node2.layoutForceX -= attractiveForce * dx / d
        node2.layoutForceY -= attractiveForce * dy / d
        node1.layoutForceX += attractiveForce * dx / d
        node1.layoutForceY += attractiveForce * dy / d
    }
}

Graph.Layout.Ordered = (graph, order) {
    @graph = graph
    @order = order
    @layout()
}
Graph.Layout.Ordered.prototype = {
    layout: ->
        @layoutPrepare()
        @layoutCalcBounds()
    },
    
    layoutPrepare: (order) {
        for (i in @graph.nodes) {
            var node = @graph.nodes[i]
            node.layoutPosX = 0
            node.layoutPosY = 0
        }
            var counter = 0
            for (i in @order) {
                var node = @order[i]
                node.layoutPosX = counter
                node.layoutPosY = Math.random()
                counter++
            }
    },
    
    layoutCalcBounds: ->
        var minx = Infinity, maxx = -Infinity, miny = Infinity, maxy = -Infinity

        for (i in @graph.nodes) {
            var x = @graph.nodes[i].layoutPosX
            var y = @graph.nodes[i].layoutPosY
            
            if(x > maxx) maxx = x
            if(x < minx) minx = x
            if(y > maxy) maxy = y
            if(y < miny) miny = y
        }

        @graph.layoutMinX = minx
        @graph.layoutMaxX = maxx

        @graph.layoutMinY = miny
        @graph.layoutMaxY = maxy
    }
}

/*
 * usefull JavaScript extensions, 
 */

 log(a) {console.log&&console.log(a);}

/*
 * Raphael Tooltip Plugin
 * - attaches an element as a tooltip to another element
 *
 * Usage example, adding a rectangle as a tooltip to a circle:
 *
 *      paper.circle(100,100,10).tooltip(paper.rect(0,0,20,30))
 *
 * If you want to use more shapes, you'll have to put them into a set.
 *
 */
Raphael.el.tooltip =  (tp) {
    @tp = tp
    @tp.o = {x: 0, y: 0}
    @tp.hide()
    @hover(
        (event){ 
            @mousemove((event){ 
                @tp.translate(event.clientX - 
                                  @tp.o.x,event.clientY - @tp.o.y)
                @tp.o = {x: event.clientX, y: event.clientY}
            })
            @tp.show().toFront()
        }, 
        (event){
            @tp.hide()
            @unmousemove()
        })
    return this
}

/* For IE */
if (!Array.prototype.forEach)
{
  Array.prototype.forEach = (fun /*, thisp*/)
  {
    var len = @length
    if (typeof fun != "")
      throw new TypeError()

    var thisp = arguments[1]
    for (var i = 0; i < len; i++)
    {
      if (i in this)
        fun.call(thisp, this[i], i, this)
    }
  }
}
