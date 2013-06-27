import xml
import re

class QWebEval(object):
    def __init__(self,data):
        self.data=data
    def __getitem__(self,expr):
        if self.data.has_key(expr):
            return self.data[expr]
        r=None
        try:
            r=eval(expr,self.data)
        except NameError,e:
            pass
        except AttributeError,e:
            pass
        except Exception,e:
            print "qweb: expression error '%s' "%expr,e
        if self.data.has_key("__builtins__"):
            del self.data["__builtins__"]
        return r
    def eval_object(self,expr):
        return self[expr]
    def eval_str(self,expr):
        if expr=="0":
            return self.data[0]
        if isinstance(self[expr],unicode):
            return self[expr].encode("utf8")
        return str(self[expr])
    def eval_format(self,expr):
        try:
            return str(expr%self)
        except:
            return "qweb: format error '%s' "%expr
#       if isinstance(r,unicode):
#           return r.encode("utf8")
    def eval_bool(self,expr):
        if self.eval_object(expr):
            return 1
        else:
            return 0

class QWebXml(object):
    """QWeb Xml templating engine
    
    The templating engine use a very simple syntax, "magic" xml attributes, to
    produce any kind of texutal output (even non-xml).
    
    QWebXml:
        the template engine core implements the basic magic attributes:
    
        t-att t-raw t-esc t-if t-foreach t-set t-call t-trim
    

    - loader: function that return a template


    """
    def __init__(self, loader):
        self.loader = loader
        self.node=xml.dom.Node
        self._t={}
        self._render_tag={}

        prefix='render_tag_'
        for i in [j for j in dir(self) if j.startswith(prefix)]:
            name=i[len(prefix):].replace('_','-')
            self._render_tag[name]=getattr(self.__class__,i)

        self._render_att={}
        prefix='render_att_'
        for i in [j for j in dir(self) if j.startswith(prefix)]:
            name=i[len(prefix):].replace('_','-')
            self._render_att[name]=getattr(self.__class__,i)

    def register_tag(self,tag,func):
        self._render_tag[tag]=func
    def add_template(self,x):
        if hasattr(x,'documentElement'):
            dom=x
        elif x.startswith("<?xml"):
            import xml.dom.minidom
            dom=xml.dom.minidom.parseString(x)
        else:
            import xml.dom.minidom
            dom=xml.dom.minidom.parse(x)
        for n in dom.documentElement.childNodes:
            if n.nodeName=="t":
                self._t[str(n.getAttribute("t-name"))]=n
    def get_template(self,name):
        if name in self._t:
            return self._t[name]
        else:
            xml = loader(name)
            add_template(xml)
            if name in self._t:
                return self._t[name]
        return 'qweb: template "%s" not found' % name


    def eval_object(self,expr,v):
        return QWebEval(v).eval_object(expr)
    def eval_str(self,expr,v):
        return QWebEval(v).eval_str(expr)
    def eval_format(self,expr,v):
        return QWebEval(v).eval_format(expr)
    def eval_bool(self,expr,v):
        return QWebEval(v).eval_bool(expr)

    def render(self,tname,v={},out=None):
        return self.render_node(self.get_template(tname),v)
    def render_node(self,e,v):
        r=""
        if e.nodeType==self.node.TEXT_NODE or e.nodeType==self.node.CDATA_SECTION_NODE:
            r=e.data.encode("utf8")
        elif e.nodeType==self.node.ELEMENT_NODE:
            pre=""
            g_att=""
            t_render=None
            t_att={}
            for (an,av) in e.attributes.items():
                an=str(an)
                if isinstance(av,types.UnicodeType):
                    av=av.encode("utf8")
                else:
                    av=av.nodeValue.encode("utf8")
                if an.startswith("t-"):
                    for i in self._render_att:
                        if an[2:].startswith(i):
                            g_att+=self._render_att[i](self,e,an,av,v)
                            break
                    else:
                        if self._render_tag.has_key(an[2:]):
                            t_render=an[2:]
                        t_att[an[2:]]=av
                else:
                    g_att+=' %s="%s"'%(an,cgi.escape(av,1));
            if t_render:
                if self._render_tag.has_key(t_render):
                    r=self._render_tag[t_render](self,e,t_att,g_att,v)
            else:
                r=self.render_element(e,g_att,v,pre,t_att.get("trim",0))
        return r
    def render_element(self,e,g_att,v,pre="",trim=0):
        g_inner=[]
        for n in e.childNodes:
            g_inner.append(self.render_node(n,v))
        name=str(e.nodeName)
        inner="".join(g_inner)
        if trim==0:
            pass
        elif trim=='left':
            inner=inner.lstrip()
        elif trim=='right':
            inner=inner.rstrip()
        elif trim=='both':
            inner=inner.strip()
        if name=="t":
            return inner
        elif len(inner):
            return "<%s%s>%s%s</%s>"%(name,g_att,pre,inner,name)
        else:
            return "<%s%s/>"%(name,g_att)

    # Attributes
    def render_att_att(self,e,an,av,v):
        if an.startswith("t-attf-"):
            att,val=an[7:],self.eval_format(av,v)
        elif an.startswith("t-att-"):
            att,val=(an[6:],self.eval_str(av,v))
        else:
            att,val=self.eval_object(av,v)
        return ' %s="%s"'%(att,cgi.escape(val,1))

    # Tags
    def render_tag_raw(self,e,t_att,g_att,v):
        return self.eval_str(t_att["raw"],v)
    def render_tag_rawf(self,e,t_att,g_att,v):
        return self.eval_format(t_att["rawf"],v)
    def render_tag_esc(self,e,t_att,g_att,v):
        return cgi.escape(self.eval_str(t_att["esc"],v))
    def render_tag_escf(self,e,t_att,g_att,v):
        return cgi.escape(self.eval_format(t_att["escf"],v))
    def render_tag_foreach(self,e,t_att,g_att,v):
        expr=t_att["foreach"]
        enum=self.eval_object(expr,v)
        if enum!=None:
            var=t_att.get('as',expr).replace('.','_')
            d=v.copy()
            size=-1
            if isinstance(enum,types.ListType):
                size=len(enum)
            elif isinstance(enum,types.TupleType):
                size=len(enum)
            elif hasattr(enum,'count'):
                size=enum.count()
            d["%s_size"%var]=size
            d["%s_all"%var]=enum
            index=0
            ru=[]
            for i in enum:
                d["%s_value"%var]=i
                d["%s_index"%var]=index
                d["%s_first"%var]=index==0
                d["%s_even"%var]=index%2
                d["%s_odd"%var]=(index+1)%2
                d["%s_last"%var]=index+1==size
                if index%2:
                    d["%s_parity"%var]='odd'
                else:
                    d["%s_parity"%var]='even'
                if isinstance(i,types.DictType):
                    d.update(i)
                else:
                    d[var]=i
                ru.append(self.render_element(e,g_att,d))
                index+=1
            return "".join(ru)
        else:
            return "qweb: t-foreach %s not found."%expr
    def render_tag_if(self,e,t_att,g_att,v):
        if self.eval_bool(t_att["if"],v):
            return self.render_element(e,g_att,v)
        else:
            return ""
    def render_tag_call(self,e,t_att,g_att,v):
        # TODO t-prefix
        if t_att.has_key("import"):
            d=v
        else:
            d=v.copy()
        d[0]=self.render_element(e,g_att,d)
        return self.render(t_att["call"],d)
    def render_tag_set(self,e,t_att,g_att,v):
        if t_att.has_key("eval"):
            v[t_att["set"]]=self.eval_object(t_att["eval"],v)
        else:
            v[t_att["set"]]=self.render_element(e,g_att,v)
        return ""

#
