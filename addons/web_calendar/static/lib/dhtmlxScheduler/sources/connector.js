/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
/*
	dhx_sort[index]=direction
	dhx_filter[index]=mask
*/
if (window.dhtmlXGridObject){
	dhtmlXGridObject.prototype._init_point_connector=dhtmlXGridObject.prototype._init_point;
	dhtmlXGridObject.prototype._init_point=function(){
		var clear_url=function(url){
			url=url.replace(/(\?|\&)connector[^\f]*/g,"");
			return url+(url.indexOf("?")!=-1?"&":"?")+"connector=true"+(this.hdr.rows.length > 0 ? "&dhx_no_header=1":"");
		};
		var combine_urls=function(url){
			return clear_url.call(this,url)+(this._connector_sorting||"")+(this._connector_filter||"");
		};
		var sorting_url=function(url,ind,dir){
			this._connector_sorting="&dhx_sort["+ind+"]="+dir;
			return combine_urls.call(this,url);
		};
		var filtering_url=function(url,inds,vals){
			for (var i=0; i<inds.length; i++)
				inds[i]="dhx_filter["+inds[i]+"]="+encodeURIComponent(vals[i]);
			this._connector_filter="&"+inds.join("&");
			return combine_urls.call(this,url);
		};
		this.attachEvent("onCollectValues",function(ind){
			if (this._con_f_used[ind]){
				if (typeof(this._con_f_used[ind]) == "object")
					return this._con_f_used[ind];
				else
					return false;
			}
			return true;
		});	
		this.attachEvent("onDynXLS",function(){
				this.xmlFileUrl=combine_urls.call(this,this.xmlFileUrl);
				return true;
		});				
		this.attachEvent("onBeforeSorting",function(ind,type,dir){
			if (type=="connector"){
				var self=this;
				this.clearAndLoad(sorting_url.call(this,this.xmlFileUrl,ind,dir),function(){
					self.setSortImgState(true,ind,dir);
				});
				return false;
			}
			return true;
		});
		this.attachEvent("onFilterStart",function(a,b){
			if (this._con_f_used.length){
				this.clearAndLoad(filtering_url.call(this,this.xmlFileUrl,a,b));
				return false;
			}
			return true;
		});
		this.attachEvent("onXLE",function(a,b,c,xml){
			if (!xml) return;
		});
		
		if (this._init_point_connector) this._init_point_connector();
	};
	dhtmlXGridObject.prototype._con_f_used=[];
	dhtmlXGridObject.prototype._in_header_connector_text_filter=function(t,i){
		if (!this._con_f_used[i])
			this._con_f_used[i]=1;
		return this._in_header_text_filter(t,i);
	};
	dhtmlXGridObject.prototype._in_header_connector_select_filter=function(t,i){
		if (!this._con_f_used[i])
			this._con_f_used[i]=2;
		return this._in_header_select_filter(t,i);
	};
	dhtmlXGridObject.prototype.load_connector=dhtmlXGridObject.prototype.load;
	dhtmlXGridObject.prototype.load=function(url, call, type){
		if (!this._colls_loaded && this.cellType){
			var ar=[];
			for (var i=0; i < this.cellType.length; i++)
				if (this.cellType[i].indexOf("co")==0 || this._con_f_used[i]==2) ar.push(i);
			if (ar.length)
				arguments[0]+=(arguments[0].indexOf("?")!=-1?"&":"?")+"connector=true&dhx_colls="+ar.join(",");
		}
		return this.load_connector.apply(this,arguments);
	};
	dhtmlXGridObject.prototype._parseHead_connector=dhtmlXGridObject.prototype._parseHead;
	dhtmlXGridObject.prototype._parseHead=function(url, call, type){
		this._parseHead_connector.apply(this,arguments);
		if (!this._colls_loaded){
			var cols = this.xmlLoader.doXPath("./coll_options", arguments[0]);
			for (var i=0; i < cols.length; i++){
				var f = cols[i].getAttribute("for");
				var v = [];
				var combo=null;
				if (this.cellType[f] == "combo")
					combo = this.getColumnCombo(f);
				if (this.cellType[f].indexOf("co")==0)
					combo=this.getCombo(f);
					
				var os = this.xmlLoader.doXPath("./item",cols[i]);
				for (var j=0; j<os.length; j++){
					var val=os[j].getAttribute("value");
					
					if (combo){
						var lab=os[j].getAttribute("label")||val;
						
						if (combo.addOption)
							combo.addOption([[val, lab]]);
						else
							combo.put(val,lab);
							
						v[v.length]=lab;
					} else
						v[v.length]=val;
				}
				if (this._con_f_used[f*1])
					this._con_f_used[f*1]=v;
			}
			this._colls_loaded=true;
		}
	};
}

if (window.dataProcessor){
	dataProcessor.prototype.init_original=dataProcessor.prototype.init;
	dataProcessor.prototype.init=function(obj){
		this.init_original(obj);
		obj._dataprocessor=this;
		
		this.setTransactionMode("POST",true);
		this.serverProcessor+=(this.serverProcessor.indexOf("?")!=-1?"&":"?")+"editing=true";
	};
}
dhtmlxError.catchError("LoadXML",function(a,b,c){
    if (c[0].status != 0) {
        alert(c[0].responseText);
    }
});
