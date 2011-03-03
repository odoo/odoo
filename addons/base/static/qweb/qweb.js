// vim:set noet fdm=syntax fdl=0 fdc=3 fdn=2:
//---------------------------------------------------------
// QWeb javascript
//---------------------------------------------------------

{
/*
	TODO

		String parsing
			if (window.DOMParser) {
				parser=new DOMParser();
				xmlDoc=parser.parseFromString(text,"text/xml");
			} else {
				xmlDoc=new ActiveXObject("Msxml2.DOMDocument.4.0");
				xmlDoc=new ActiveXObject("Microsoft.XMLDOM");
					Which versions to try, it's confusing...
				xmlDoc.async="false";
				xmlDoc.async=false;
				xmlDoc.preserveWhiteSpace=true;
				xmlDoc.load("f.xml");
				xmlDoc.loadXML(text);  ?
			}

		Support space in IE by reparsing the responseText
			xmlhttp.responseXML.loadXML(xmlhttp.responseText); ?

		Preprocess: (nice optimization) 
			preprocess by flattening all non t- element to a TEXT_NODE.
			count the number of "\n" in text nodes to give an aproximate LINE NUMBER on elements for error reporting
			if from IE HTMLDOM use if(a[i].specified) to avoid 88 empty attributes per element during the preprocess, 

		implement t-trim 'left' 'right' 'both', is it needed ? inner=render_trim(l_inner.join(), t_att)

		Ruby/python: to backport from javascript to python/ruby render_node to use regexp, factorize foreach %var, t-att test for tuple(attname,value)

	DONE
		we reintroduced t-att-id, no more t-esc-id because of the new convention t-att="["id","val"]"
*/
}

var QWeb={
	templates:{},
	prefix:"t",
	reg:"",
	tag:{},
	att:{},
	eval_object:function(e,v) {
		// TODO: Currently this will also replace and, or, ... in strings. Try
		// 'hi boys and girls' != '' and 1 == 1  -- will be replaced to : 'hi boys && girls' != '' && 1 == 1
		// try to find a solution without tokenizing
		e = e.replace(/\Wand\W/g, " && ");
		e = e.replace(/\Wor\W/g, " and ");
		e = e.replace(/\Wgt\W/g, " > ");
		e = e.replace(/\Wgte\W/g, " >= ");
		e = e.replace(/\Wlt\W/g, " < ");
		e = e.replace(/\Wlte\W/g, " <= ");
		if(v[e]!=undefined) {
			return v[e]
		} else {
			with(v) return eval(e);
		}
	},
	eval_str:function(e,v){
		var r=this.eval_object(e,v)
		r=(typeof(r)=="undefined"||r==null) ? "" : r.toString()
		return e=="0" ? v["0"] : r
	},
	eval_format:function(e,v){
		var i,m,r,src=e.split(/#/)
		r=src[0]
		for(i=1; i<src.length; i++) {
			if(m=src[i].match(/^{(.*)}(.*)/)) {
				r+=this.eval_str(m[1],v)+m[2]
			} else {
				r+="#"+src[i]
			}
		}
		return r
	},
	eval_bool:function(e,v){
		return this.eval_object(e,v)?true:false;
	},
	escape_text:function(s){
		return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
	},
	escape_att:function(s){
		return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")
	},
	render_node:function(e,v){
		var r=""
		if(e.nodeType==3) {
			r=e.data;
		} else if(e.nodeType==1) {
			var g_att={};
			var t_att={};
			var t_render=null;
			var a=e.attributes;
			for(var i=0; i<a.length; i++) {
				var an=a[i].name,av=a[i].value;
				var m,n;
				if(m=an.match(this.reg)) {
					n=m[1]
					if(n=="eval") {
						n=m[2].substring(1)
						av=this.eval_str(av, v)
					}
					if(f=this.att[n]) {
						this[f](e,t_att,g_att,v,m[2],av)
					} else if(f=this.tag[n]) {
						t_render=f
					}
					t_att[n]=av
				} else {
					g_att[an]=av
				}
			}
			if (t_render) {
				r = this[t_render](e, t_att, g_att, v)
			} else {
				r = this.render_element(e, t_att, g_att, v)
			}
		} 
		return r;
	},
	render_element:function(e,t_att,g_att,v){
		var inner="",ec=e.childNodes;
		for (var i=0; i<ec.length; i++) {
			inner+=this.render_node(ec[i],v)
		}
		if(e.tagName==this.prefix) {
			return inner;
		} else {
			var att="";
			for(var an in g_att) {
				av=g_att[an]
				att+=" "+an+'="'+this.escape_att(av)+'"'
			}
			r=inner.length ? "<"+e.tagName+att+">"+inner+"</"+e.tagName+">" : "<"+e.tagName+att+"/>"
			return r
		}
	},
	render_att_att:function(e,t_att,g_att,v,ext,av){
		if(ext) {
			g_att[ext.substring(1)]=this.eval_str(av,v)
		} else {
			o=this.eval_object(av,v)
			g_att[o[0]]=o[1]
		}
	},
	render_att_attf:function(e,t_att,g_att,v,ext,av){
		g_att[ext.substring(1)]=this.eval_format(av,v)
	},
	render_tag_raw:function(e,t_att,g_att,v){
		return this.eval_str(t_att["raw"], v);
	},
	render_tag_rawf:function(e,t_att,g_att,v){
		return this.eval_format(t_att["raw"], v);
	},
	render_tag_esc:function(e,t_att,g_att,v){
		return this.escape_text(this.eval_str(t_att["esc"], v));
	},
	render_tag_escf:function(e,t_att,g_att,v){
		return this.escape_text(this.eval_format(t_att["esc"], v));
	},
	render_tag_if:function(e,t_att,g_att,v){
		return this.eval_bool(t_att["if"],v) ? this.render_element(e, t_att, g_att, v) : ""
	},
	render_tag_set:function(e,t_att,g_att,v){
		var ev=t_att["value"]
		if(ev && ev.constructor!=Function) {
			v[t_att["set"]]=this.eval_object(ev,v)
		} else {
			v[t_att["set"]]=this.render_element(e, t_att, g_att, v)
		}
		return ""
	},
	render_tag_call:function(e,t_att,g_att,v){
		var d=v;
		if(!t_att["import"]) {
			d = {}
			for(var i in v) {
				d[i]=v[i]
			}
		}
		d["0"]=this.render_element(e, t_att, g_att, d)
		return this.render(t_att["call"],d)
	},
	render_tag_js:function(e,t_att,g_att,v){
		var r=this.eval_str(this.render_element(e, t_att, g_att, v),v)
		return t_att["js"]!="quiet" ? r : ""
	},
	render_tag_foreach:function(e,t_att,g_att,v){
		var expr=t_att["foreach"]
		var enu=this.eval_object(expr,v)
		var ru=[];
		if(enu) {
			var val=t_att['as'] || expr.replace(/[^a-zA-Z0-9]/g,'_')
			d={}
			for(var i in v) {
				d[i]=v[i]
			}
			d[val+"_all"]=enu
			val_value  = val+"_value"
			val_index  = val+"_index"
			val_first  = val+"_first"
			val_last   = val+"_last"
			val_parity = val+"_parity"
			var size=enu.length
			if(size) {
				d[val+"_size"]=size
				for (var i=0; i<size; i++) {
					var cur=enu[i]
					d[val_value]=cur
					d[val_index]=i
					d[val_first]=i==0
					d[val_last]=i+1==size
					d[val_parity]=(i%2==1 ? 'odd' : 'even')
					if (cur.constructor==Object) {
						for(var j in cur) {
							d[j]=cur[j]
						}
					}
					d[val]=cur
					var r = this.render_element(e,t_att,g_att,d);
					ru.push(r)
				}
			} else {
				index=0
				for(cur in enu) {
					d[val_value]=cur
					d[val_index]=index
					d[val_first]=index==0
					d[val_parity]=(index%2==1 ? 'odd' : 'even')
					d[val]=cur
					ru.push(this.render_element(e,t_att,g_att,d))
					index+=1
				}
			}
			return ru.join("")
		} else {
			return "qweb: foreach "+expr+" not found."
		}
	},
	hash:function(){
		var l=[]
		for(var i in this) {
			if(m=i.match(/render_tag_(.*)/)) {
				this.tag[m[1]]=i
				l.push(m[1])
			} else if(m=i.match(/render_att_(.*)/)) {
				this.att[m[1]]=i
				l.push(m[1])
			}
		}
		l.sort(function(a,b){return a.length>b.length?-1:1})
		var s="^"+this.prefix+"-(eval|"+l.join("|")+"|.*)(.*)$"
		this.reg=new RegExp(s);
	},
	load_xml:function(s){
		var xml;
		if(s[0]=="<") {
			/*
				manque ca pour sarrisa
			if(window.DOMParser){
				mozilla
			if(!window.DOMParser){
				var doc = Sarissa.getDomDocument();
				doc.loadXML(sXml);
				return doc;
				};
			};
		*/
		} else {
			var w=window,r=w.XMLHttpRequest,j;
			if(r)r=new r();else for(j in{"Msxml2":1,"Microsoft":1})try{r=new ActiveXObject(j+".XMLHTTP");break}catch(e){}
			if(r) {
				r.open("GET", s, false);
				r.send(null);
				//if ie r.setRequestHeader("If-Modified-Since", "Sat, 1 Jan 2000 00:00:00 GMT");
				xml=r.responseXML;
				/*
					TODO
					if intsernetexploror
					getdomimplmentation() for try catch
					responseXML.getImplet
					d=domimple()
					d.preserverWhitespace=1
					d.loadXML()

					xml.preserverWhitespace=1
					xml.loadXML(r.reponseText)
				*/
				return xml;
			}
		}
	},
	add_template:function(e){
		// TODO: keep sources so we can implement reload()
		this.hash()
		if(e.constructor==String) {
			e=this.load_xml(e)
		}
		var ec=[];
		if(e.documentElement) {
			ec=e.documentElement.childNodes
		} else if(e.childNodes) {
			ec=e.childNodes
		}
		for (var i=0; i<ec.length; i++) {
			var n=ec[i];
			if(n.nodeType==1) {
				var name=n.getAttribute(this.prefix+"-name")
				this.templates[name]=n;
			}
		}
	},
	render:function(name,v){
		if(e=this.templates[name]) {
			return this.render_node(e,v)
		} else {
			return "template "+name+" not found";
		}
	},
	dump:function(o){
		var r="";
		if(typeof(o)=="object") {
			for(var i in o) {
				r+=i+" : "+this.dump(s)+"\n"
			}
			r=s+"{\n"+r+"}\n"
		} else {
			r=s+"";
		}
		return r;
	},
	debug:function(s){
		var r=this.dump(s)
		$("#debug")[0].append(this.escape_text(r)+"<br/>\n")
	}
}

