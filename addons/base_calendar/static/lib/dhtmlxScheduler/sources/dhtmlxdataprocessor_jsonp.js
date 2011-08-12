/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
if(dataProcessor) {
    dataProcessor.prototype.enableJSONP = function(mode) {
        if(mode) {
            this._jsonp_attach_id = this.attachEvent("onBeforeDataSending", function(rowId,rowIdState,a1){
                if (rowId)
                    this._in_progress[rowId]=(new Date()).valueOf();

                var url = this.serverProcessor+(this._user?(getUrlSymbol(this.serverProcessor)+["dhx_user="+this._user,"dhx_version="+this.obj.getUserData(0,"version")].join("&")):"");
                url += ((url.indexOf("?")!=-1)?"&":"?")+this.serialize(a1,rowId);

                this._jsonp(url, [], function(data){
                    var xml = new dtmlXMLLoaderObject(this.afterUpdate,this,true);
                    xml.loadXMLString(data);
                    this.afterUpdate(this, null, null, null, xml);
                }, this);

                this._waitMode++;
                return false;
            });
        }
        else {
            if(this._jsonp_attach_id)
                this.detachEvent(this._jsonp_attach_id);
        }
    };
    dataProcessor.prototype._jsonp = function(url, params, callback, master){
        var global_obj = "dataProcessor";
        var id = "dp_jsonp_"+new Date().valueOf();
        var script = document.createElement('script');
        script.id = id;
        script.type = 'text/javascript';

        var head = document.getElementsByTagName("head")[0];

        if (!params)
            params = {};
        params.jsonp = global_obj+"."+id; // would be called as dataProcessor.dp_jsonp_1938948394
        dataProcessor[id]=function(){
            callback.apply(master||window, arguments);
            script.parentNode.removeChild(script);
            callback = head = master = script = null;
            delete dataProcessor[id];
        };

        var vals = [];
        for (var key in params) vals.push(key+"="+encodeURIComponent(params[key]));

        url += (url.indexOf("?") == -1 ? "?" : "&")+vals.join("&");

        script.src = url ;
        head.appendChild(script);
    };
}
