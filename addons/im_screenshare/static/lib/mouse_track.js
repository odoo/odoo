

var CursorMirror = (function(){

    function CursorMirror(){
        this.fps = 24;
        this.newCoords = {};
        this.counter = 0;
        this.interval = Math.round(1000/this.fps);
        this.play = null;
    };

    CursorMirror.prototype.computeRatio = function(originPageDim) {
        var actualPage = smt2fn.getPageSize();
        var discrepanceRatio = {};
        discrepanceRatio.x = smt2fn.roundTo(actualPage.width / originPageDim.width);
        discrepanceRatio.y = smt2fn.roundTo(actualPage.height / originPageDim.height);
        return discrepanceRatio;
    };

    CursorMirror.prototype.forwardData = function(originPageDim, coords, elem) {
        var ratio = this.computeRatio(originPageDim);
        coords.x = _.map(coords.x, function(num){ return num * ratio.x; });
        coords.y = _.map(coords.y, function(num){ return num * ratio.y; });
        this.newCoords = coords;
        this.replay();
    };

    CursorMirror.prototype.replay = function() {
        if(this.counter < this.newCoords.x.length){
            var x = this.newCoords.x[this.counter];
            var y = this.newCoords.y[this.counter];
            // create the mouse canvas
            $("#odoo-screenshare-mousecanvas").remove();
            var mouse = $('<div/>', {
                id: 'odoo-screenshare-mousecanvas',
                class: 'oe_screenshare-mouse'
            });
            $(document).find('html').append(mouse);
            mouse.css('left', x+'px').css('top', y+'px');

            this.counter++;
            this.play = setInterval(this.replay(), this.interval);
        }else{
            this.counter = 0;
            clearInterval(this.play);
        }
    };

    return CursorMirror;
})();


var CursorMirrorClient = (function(){

    function CursorMirrorClient(mirror){
        this.mirror = mirror;
        this.mouse = {
                x: 0,
                y: 0
        };
        this.page = {
                width: 0,
                height: 0
        };
        this.coords = {
                x: [],
                y: [],
                p: []
        };
        this.elem = {
                hovered: [],
                clicked: []
        };
        this.clicked = false;
        this.recordingInterval = null;
        this.fps = 2;

        // event handler (need to be saved to allow removal, in disconnect method)
        this.onMouseDownMoveHandler = this.onPress.bind(this);
        this.onMouseMoveHandler = this.onMove.bind(this);
        this.onMouseUpHandler = this.releaseClick.bind(this);
        this.onResizeHandler = this.computeAvailableSpace.bind(this);

        document.addEventListener('mousedown', this.onMouseDownMoveHandler, false);
        document.addEventListener('mousemove', this.onMouseMoveHandler, false);
        document.addEventListener('mouseup', this.onMouseUpHandler, false);
        window.addEventListener('resize', this.onResizeHandler, false);

        this.computeAvailableSpace();
        this.interval = Math.round(1000/this.fps);
        this.recordingInterval = setInterval(_.bind(this.recMouse, this), this.interval);
    };

    CursorMirrorClient.prototype.computeAvailableSpace = function() {
        var doc = smt2fn.getPageSize();
        this.page.width  = doc.width;
        this.page.height = doc.height;
    };

    CursorMirrorClient.prototype.findElement = function(e) {
        if (!e) {
            e = window.event;
        }
        // bind function to widget tracking object
        smt2fn.widget.findDOMElement(e, function(name){
            if (e.type == "mousedown" || e.type == "touchstart") {
                this.elem.clicked.push(name);
            } else if (e.type == "mousemove" || e.type == "touchmove") {
                this.elem.hovered.push(name);
            }
        });
    };

    CursorMirrorClient.prototype.getMousePos = function(e) {
        if (!e) {
            var e = window.event;
        }
        var x = 0, y = 0;
        if (e.pageX || e.pageY) {
            x = e.pageX;
            y = e.pageY;
        } else if (e.clientX || e.clientY) {
            x = e.clientX + document.body.scrollLeft + document.documentElement.scrollLeft;
            y = e.clientY + document.body.scrollTop  + document.documentElement.scrollTop;
        }
        // in certain situations the mouse coordinates could be negative values (e.g. Opera)
        if (x < 0 || !x) x = 0;
        if (y < 0 || !y) y = 0;
        return {'x': x, 'y': y};
    };

    CursorMirrorClient.prototype.onMove = function(e) {
        if (e.touches) {
            e = e.touches[0] || e.targetTouches[0];
        }
        var p = this.getMousePos(e);
        this.coords.x.push(p.x);
        this.coords.y.push(p.y);
    };

    CursorMirrorClient.prototype.onPress = function(e){
        if (e.touches) {
            e = e.touches[0] || e.targetTouches[0];
        }
        this.setClick();
    };

    CursorMirrorClient.prototype.releaseClick = function() {
        this.clicked = false;
    };

    CursorMirrorClient.prototype.setClick = function() {
        this.clicked = true;
    };

    CursorMirrorClient.prototype.forwardData = function() {
        this.mirror.forwardData(this.page, this.coords, this.elem);
    };

    CursorMirrorClient.prototype.clearMouseData = function() {
        this.coords.x = [];
        this.coords.y = [];
        this.coords.p = [];
        this.elem.hovered = [];
        this.elem.clicked = [];
    };

    CursorMirrorClient.prototype.recMouse = function() {
        this.forwardData();
        this.clearMouseData();
    };

    CursorMirrorClient.prototype.disconnect = function() {
        clearInterval(this.recordingInterval);
        // unbind event handler
        document.removeEventListener('mousedown', this.onMouseDownMoveHandler, false);
        document.removeEventListener('mousemove', this.onMouseMoveHandler, false);
        document.removeEventListener('mouseup', this.onMouseUpHandler, false);
        window.removeEventListener('resize', this.onResizeHandler, false);
    };

    return CursorMirrorClient;
})();
