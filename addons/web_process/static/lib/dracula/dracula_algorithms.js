/*
 * Various algorithms and data structures, licensed under the MIT-license.
 * (c) 2010 by Johann Philipp Strathausen <strathausen@gmail.com>
 * http://strathausen.eu
 *
 */



/*
        Bellman-Ford
    
    Path-finding algorithm, finds the shortest paths from one node to all nodes.
    
    
        Complexity
        
    O( |E| · |V| ), where E = edges and V = vertices (nodes)
    
    
        Constraints
    
    Can run on graphs with negative edge weights as long as they do not have
    any negative weight cycles.
    
 */
function bellman_ford(g, source) {

    /* STEP 1: initialisation */
    for(var n in g.nodes)
        g.nodes[n].distance = Infinity;
        /* predecessors are implicitly null */
    source.distance = 0;
    
    step("Initially, all distances are infinite and all predecessors are null.");
    
    /* STEP 2: relax each edge (this is at the heart of Bellman-Ford) */
    /* repeat this for the number of nodes minus one */
    for(var i = 1; i < g.nodes.length; i++)
        /* for each edge */
        for(var e in g.edges) {
            var edge = g.edges[e];
            if(edge.source.distance + edge.weight < edge.target.distance) {
                step("Relax edge between " + edge.source.id + " and " + edge.target.id + ".");
                edge.target.distance = edge.source.distance + edge.weight;
                edge.target.predecessor = edge.source;
            }
	    //Added by Jake Stothard (Needs to be tested)
	    if(!edge.style.directed) {
		if(edge.target.distance + edge.weight < edge.source.distance) {
                    g.snapShot("Relax edge between "+edge.target.id+" and "+edge.source.id+".");
                    edge.source.distance = edge.target.distance + edge.weight;
                    edge.source.predecessor = edge.target;
		}
	    }
        }
    step("Ready.");
    
    /* STEP 3: TODO Check for negative cycles */
    /* For now we assume here that the graph does not contain any negative
       weights cycles. (this is left as an excercise to the reader[tm]) */
}



/*
   Path-finding algorithm Dijkstra
   
   - worst-case running time is O((|E| + |V|) · log |V| ) thus better than
     Bellman-Ford for sparse graphs (with less edges), but cannot handle
     negative edge weights
 */
function dijkstra(g, source) {

    /* initially, all distances are infinite and all predecessors are null */
    for(var n in g.nodes)
        g.nodes[n].distance = Infinity;
        /* predecessors are implicitly null */

    g.snapShot("Initially, all distances are infinite and all predecessors are null.");

    source.distance = 0;
    /* set of unoptimized nodes, sorted by their distance (but a Fibonacci heap
       would be better) */
    var q = new BinaryMinHeap(g.nodes, "distance");

    /* pointer to the node in focus */
    var node;

    /* get the node with the smallest distance
       as long as we have unoptimized nodes. q.min() can have O(log n). */
    while(q.min() != undefined) {
        /* remove the latest */
        node = q.extractMin();
        node.optimized = true;

        /* no nodes accessible from this one, should not happen */
        if(node.distance == Infinity)
            throw "Orphaned node!";

        /* for each neighbour of node */
        for(e in node.edges) {
	    var other = (node == node.edges[e].target) ? node.edges[e].source : node.edges[e].target;
		
            if(other.optimized)
                continue;

            /* look for an alternative route */
            var alt = node.distance + node.edges[e].weight;
            
            /* update distance and route if a better one has been found */
            if (alt < other.distance) {
            
                /* update distance of neighbour */
                other.distance = alt;

                /* update priority queue */
                q.heapify();

                /* update path */
                other.predecessor = node;
                g.snapShot("Enhancing node.")
            }
        }
    }
}


/* All-Pairs-Shortest-Paths */
/* Runs at worst in O(|V|³) and at best in Omega(|V|³) :-)
   complexity Sigma(|V|²) */
/* This implementation is not yet ready for general use, but works with the
   Dracula graph library. */
function floyd_warshall(g, source) {

    /* Step 1: initialising empty path matrix (second dimension is implicit) */
    var path = [];
    var next = [];
    var n = g.nodes.length;

    /* construct path matrix, initialize with Infinity */
    for(j in g.nodes) {
        path[j] = [];
        next[j] = [];
        for(i in g.nodes)
            path[j][i] = j == i ? 0 : Infinity;
    }   
    
    /* initialize path with edge weights */
    for(e in g.edges)
        path[g.edges[e].source.id][g.edges[e].target.id] = g.edges[e].weight;
    
    /* Note: Usually, the initialisation is done by getting the edge weights
       from a node matrix representation of the graph, not by iterating through
       a list of edges as done here. */
    
    /* Step 2: find best distances (the heart of Floyd-Warshall) */
    for(k in g.nodes){
        for(i in g.nodes) {
            for(j in g.nodes)
                if(path[i][j] > path[i][k] + path[k][j]) {
                    path[i][j] = path[i][k] + path[k][j];
                    /* Step 2.b: remember the path */
                    next[i][j] = k;
                }
        }
    }

    /* Step 3: Path reconstruction, get shortest path */
    function getPath(i, j) {
        if(path[i][j] == Infinity)
            throw "There is no path.";
        var intermediate = next[i][j];
        if(intermediate == undefined)
            return null;
        else
            return getPath(i, intermediate)
                .concat([intermediate])
                .concat(getPath(intermediate, j));
    }

    /* TODO use the knowledge, e.g. mark path in graph */
}

/*
        Ford-Fulkerson
    
    Max-Flow-Min-Cut Algorithm finding the maximum flow through a directed
    graph from source to sink.
    
    
        Complexity

    O(E * max(f)), max(f) being the maximum flow
    
    
        Description

    As long as there is an open path through the residual graph, send the
    minimum of the residual capacities on the path.
    
    
        Constraints
    
    The algorithm works only if all weights are integers. Otherwise it is
    possible that the Ford–Fulkerson algorithm will not converge to the maximum
    value.
    
    
        Input
    
    g - Graph object
    s - Source ID
    t - Target (sink) ID
    
    
        Output
    
    Maximum flow from Source s to Target t

 */
/*
        Edmonds-Karp
    
    Max-Flow-Min-Cut Algorithm finding the maximum flow through a directed
    graph from source to sink. An implementation of the Ford-Fulkerson
    algorithm.
    
    
        Complexity
    
    O(|V|*|E|²)
    
    
        Input
        
    g - Graph object (with node and edge lists, capacity is a property of edge)
    s - source ID
    t - sink ID
    
 */
function edmonds_karp(g, s, t) {

}

/*
   A simple binary min-heap serving as a priority queue
   - takes an array as the input, with elements having a key property
   - elements will look like this:
        {
            key: "... key property ...", 
            value: "... element content ..."
        }
    - provides insert(), min(), extractMin() and heapify()
    - example usage (e.g. via the Firebug or Chromium console):
        var x = {foo: 20, hui: "bla"};
        var a = new BinaryMinHeap([x,{foo:3},{foo:10},{foo:20},{foo:30},{foo:6},{foo:1},{foo:3}],"foo");
        console.log(a.extractMin());
        console.log(a.extractMin());
        x.foo = 0; // update key
        a.heapify(); // call this always after having a key updated
        console.log(a.extractMin());
        console.log(a.extractMin());
    - can also be used on a simple array, like [9,7,8,5]
 */
function BinaryMinHeap(array, key) {
    
    /* Binary tree stored in an array, no need for a complicated data structure */
    var tree = [];
    
    var key = key || 'key';
    
    /* Calculate the index of the parent or a child */
    var parent = function(index) { return Math.floor((index - 1)/2); };
    var right = function(index) { return 2 * index + 2; };
    var left = function(index) { return 2 * index + 1; };

    /* Helper function to swap elements with their parent 
       as long as the parent is bigger */
    function bubble_up(i) {
        var p = parent(i);
        while((p >= 0) && (tree[i][key] < tree[p][key])) {
            /* swap with parent */
            tree[i] = tree.splice(p, 1, tree[i])[0];
            /* go up one level */
            i = p;
            p = parent(i);
        }
    }

    /* Helper function to swap elements with the smaller of their children
       as long as there is one */
    function bubble_down(i) {
        var l = left(i);
        var r = right(i);
        
        /* as long as there are smaller children */
        while(tree[l] && (tree[i][key] > tree[l][key]) || tree[r] && (tree[i][key] > tree[r][key])) {
            
            /* find smaller child */
            var child = tree[l] ? tree[r] ? tree[l][key] > tree[r][key] ? r : l : l : l;
            
            /* swap with smaller child with current element */
            tree[i] = tree.splice(child, 1, tree[i])[0];
            
            /* go up one level */
            i = child;
            l = left(i);
            r = right(i);
        }
    }
    
    /* Insert a new element with respect to the heap property
       1. Insert the element at the end
       2. Bubble it up until it is smaller than its parent */
    this.insert = function(element) {
    
        /* make sure there's a key property */
        (element[key] == undefined) && (element = {key:element});
        
        /* insert element at the end */
        tree.push(element);

        /* bubble up the element */
        bubble_up(tree.length - 1);
    }
    
    /* Only show us the minimum */
    this.min = function() {
        return tree.length == 1 ? undefined : tree[0];
    }
    
    /* Return and remove the minimum
       1. Take the root as the minimum that we are looking for
       2. Move the last element to the root (thereby deleting the root) 
       3. Compare the new root with both of its children, swap it with the
          smaller child and then check again from there (bubble down)
    */
    this.extractMin = function() {
        var result = this.min();
        
        /* move the last element to the root or empty the tree completely */
        /* bubble down the new root if necessary */
        (tree.length == 1) && (tree = []) || (tree[0] = tree.pop()) && bubble_down(0);
        
        return result;        
    }
    
    /* currently unused, TODO implement */
    this.changeKey = function(index, key) {
        throw "function not implemented";
    }

    this.heapify = function() {
        for(var start = Math.floor((tree.length - 2) / 2); start >= 0; start--) {
            bubble_down(start);
        }
    }
    
    /* insert the input elements one by one only when we don't have a key property (TODO can be done more elegant) */
    for(i in (array || []))
        this.insert(array[i]);
}



/*
    Quick Sort:
        1. Select some random value from the array, the median.
        2. Divide the array in three smaller arrays according to the elements
           being less, equal or greater than the median.
        3. Recursively sort the array containg the elements less than the
           median and the one containing elements greater than the median.
        4. Concatenate the three arrays (less, equal and greater).
        5. One or no element is always sorted.
    TODO: This could be implemented more efficiently by using only one array object and several pointers.
*/
function quickSort(arr) {
    /* recursion anchor: one element is always sorted */
    if(arr.length <= 1) return arr;
    /* randomly selecting some value */
    var median = arr[Math.floor(Math.random() * arr.length)];
    var arr1 = [], arr2 = [], arr3 = [];
    for(var i in arr) {
        arr[i] < median && arr1.push(arr[i]);
        arr[i] == median && arr2.push(arr[i]);
        arr[i] > median && arr3.push(arr[i]);
    }
    /* recursive sorting and assembling final result */
    return quickSort(arr1).concat(arr2).concat(quickSort(arr3));
}

/*
    Selection Sort:
        1. Select the minimum and remove it from the array
        2. Sort the rest recursively
        3. Return the minimum plus the sorted rest
        4. An array with only one element is already sorted
*/
function selectionSort(arr) {
    /* recursion anchor: one element is always sorted */
    if(arr.length == 1) return arr;
    var minimum = Infinity;
    var index;
    for(var i in arr) {
        if(arr[i] < minimum) {
            minimum = arr[i];
            index = i; /* remember the minimum index for later removal */
        }
    }
    /* remove the minimum */
    arr.splice(index, 1);
    /* assemble result and sort recursively (could be easily done iteratively as well)*/
    return [minimum].concat(selectionSort(arr));
}

/*
    Merge Sort:
        1. Cut the array in half
        2. Sort each of them recursively
        3. Merge the two sorted arrays
        4. An array with only one element is considered sorted

*/
function mergeSort(arr) {
    /* merges two sorted arrays into one sorted array */
    function merge(a, b) {
        /* result set */
        var c = [];
        /* as long as there are elements in the arrays to be merged */
        while(a.length > 0 || b.length > 0){
            /* are there elements to be merged, if yes, compare them and merge */
            var n = a.length > 0 && b.length > 0 ? a[0] < b[0] ? a.shift() : b.shift() : b.length > 0 ? b.shift() : a.length > 0 ? a.shift() : null;
            /* always push the smaller one onto the result set */
            n != null && c.push(n);
        }
        return c;
    }
    /* this mergeSort implementation cuts the array in half, wich should be fine with randomized arrays, but introduces the risk of a worst-case scenario */
    median = Math.floor(arr.length / 2);
    var part1 = arr.slice(0, median); /* for some reason it doesn't work if inserted directly in the return statement (tried so with firefox) */
    var part2 = arr.slice(median - arr.length);
    return arr.length <= 1 ? arr : merge(
        mergeSort(part1), /* first half */
        mergeSort(part2) /* second half */
    );
}

/* Balanced Red-Black-Tree */
function RedBlackTree(arr) {
    
}

function BTree(arr) {
    
}

function NaryTree(n, arr) {
    
}

/**
 * Knuth-Morris-Pratt string matching algorithm - finds a pattern in a text.
 * FIXME: Doesn't work correctly yet.
 */
function kmp(p, t) {

    /**
     * PREFIX, OVERLAP or FALIURE function for KMP. Computes how many iterations
     * the algorithm can skip after a mismatch.
     *
     * @input p - pattern (string)
     * @result array of skippable iterations
     */
    function prefix(p) {
        /* pi contains the computed skip marks */
        var pi = [0], k = 0;
        for(q = 1; q < p.length; q++) {
            while(k > 0 && (p.charAt(k) != p.charAt(q)))
                k = pi[k-1];
            
            (p.charAt(k) == p.charAt(q)) && k++;
            
            pi[q] = k;
        }
        return pi;
    }
    
    /* The actual KMP algorithm starts here. */
    
    var pi = prefix(p), q = 0, result = [];
    
    for(var i = 0; i < t.length; i++) {
        /* jump forward as long as the character doesn't match */
        while((q > 0) && (p.charAt(q) != t.charAt(i)))
            q = pi[q];
        
        (p.charAt(q) == t.charAt(i)) && q++;
        
        (q == p.length) && result.push(i - p.length) && (q = pi[q]);
    }
    
    return result;
}

/* step for algorithm visualisation */
function step(comment, funct) {
    //wait for input
    //display comment (before or after waiting)
//    next.wait();
    /* execute callback function */
    funct();
}

/**
 * Curry - Function currying
 * Copyright (c) 2008 Ariel Flesler - aflesler(at)gmail(dot)com | http://flesler.blogspot.com
 * Licensed under BSD (http://www.opensource.org/licenses/bsd-license.php)
 * Date: 10/4/2008
 *
 * @author Ariel Flesler
 * @version 1.0.1
 */
function curry( fn ){
	return function(){
		var args = curry.args(arguments),
			master = arguments.callee,
			self = this;

		return args.length >= fn.length ? fn.apply(self,args) :	function(){
			return master.apply( self, args.concat(curry.args(arguments)) );
		};
	};
};

curry.args = function( args ){
	return Array.prototype.slice.call(args);
};

Function.prototype.curry = function(){
	return curry(this);
};

/**
 * Topological Sort
 *
 * Sort a directed graph based on incoming edges
 *
 * Coded by Jake Stothard
 */
function topological_sort(g) {
    //Mark nodes as "deleted" instead of actually deleting them
    //That way we don't have to copy g

    for(i in g.nodes)
	g.nodes[i].deleted = false;
    
    var ret = topological_sort_helper(g);

    //Cleanup: Remove the deleted property
    for(i in g.nodes)
	delete g.nodes[i].deleted

    return ret;
}
function topological_sort_helper(g) {
    //Find node with no incoming edges
    var node;
    for(i in g.nodes) {
	if(g.nodes[i].deleted)
	    continue; //Bad style, meh
	
	var incoming = false;
	for(j in g.nodes[i].edges) {
	    if(g.nodes[i].edges[j].target == g.nodes[i]
	      && g.nodes[i].edges[j].source.deleted == false) {
		incoming = true;
		break;
	    }
	}
	if(!incoming) {
	    node = g.nodes[i];
	    break;
	}
    }

    // Either unsortable or done. Either way, GTFO
    if(node == undefined)
	return [];

    //"Delete" node from g
    node.deleted = true;
    
    var tail = topological_sort_helper(g);

    tail.unshift(node);

    return tail;
}
