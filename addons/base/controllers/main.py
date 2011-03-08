# -*- coding: utf-8 -*-

import glob,json,os

#import simplejson as json

import openerpweb

from xml.etree import ElementTree

class Xml2Json:
    # xml2json-direct
    # Simple and straightforward XML-to-JSON converter in Python
    # New BSD Licensed
    #
    # URL: http://code.google.com/p/xml2json-direct/
    @staticmethod
    def convert_to_json(s):
        return json.dumps(Xml2Json.convert_to_structure(s), sort_keys=True, indent=4)

    @staticmethod
    def convert_to_structure(s):
        root = ElementTree.fromstring(s)
        return Xml2Json.convert_element(root)

    @staticmethod
    def convert_element(el, skip_whitespaces=True):
        res = {}
        if el.tag[0]=="{":
            ns, name = el.tag.rsplit("}",1) 
            res["tag"] = name
            res["namespace"] = ns[1:]
        else:
            res["tag"] = el.tag
        res["attrs"] = {}
        for k,v in el.items():
            res["attrs"][k] = v
        kids = []
        if el.text and (not skip_whitespaces or el.text.strip() != ''):
            kids.append(el.text)
        for kid in el:
            kids.append(Xml2Json.convert_element(kid))
            if kid.tail and (not skip_whitespaces or kid.tail.strip() != ''):
                kids.append(kid.tail)
        if len(kids):
            res["children"] = kids
        return res

#----------------------------------------------------------
# OpenERP Web base Controllers
#----------------------------------------------------------

class Hello(openerpweb.Controller):
    _cp_path = "/base/hello"

    def index(self):
        return "hello world"

    @openerpweb.jsonrequest
    def ajax_hello_world(self,req):
        return {"welcome":"hello world"}

    @openerpweb.jsonrequest
    def ajax_hello_error(self,req):
        raise Exception("You suck")

class Connection(openerpweb.Controller):
    _cp_path = "/base/connection"

    def manifest_glob(self, modlist, key):
        files = []
        for i in modlist.split(','):
            globlist = openerpweb.addons_manifest.get(i,{}).get('css',[])
            for j in globlist:
                tmp = glob.glob(os.path.join(openerpweb.path_addons,i,j))
                files.append(tmp)
        print modlist, key, files
        return files

    def concat_files(self, file_list):
        """ Concatenate file content
        return (concat,timestamp)
        concat: concatenation of file content
        timestamp: max(os.path.getmtime of file_list)
        """
        root = openerpweb.path_root
        files_content = []
        files_timestamp = 0
        for i in file_list:
            fname = os.path.join(root,i)
            ftime = os.path.getmtime(fname)
            if ftime > files_timestamp:
                files_timestamp = ftime
            files_content = open(fname).read()
        files_concat = "".join(files_content)
        return files_concat

    def list_modules(self, req):
        return 

    @openerpweb.jsonrequest
    def manifest_files(self, req, key, mods):
        files = self.manifest_glob(mods, key)
        return {'files': files}

    def css(self, req):
        # TODO http get argument mods is a comma seprated value of modules
        mods = 'base,base_hello'
        files = self.manifest_glob(mods.split(','), 'css')
        concat = self.concat_files(files)[0]
        # TODO request set the Date of last modif and Etag
        return concat
    css.exposed=1

    def js(self, req):
        # TODO http get argument mods is a comma seprated value of modules
        mods = 'base,base_hello'
        files = self.manifest_glob(mods.split(','), 'js')
        concat = self.concat_files(files)[0]
        # TODO request set the Date of last modif and Etag
        return concat
    js.exposed=1

class Session(openerpweb.Controller):
    _cp_path = "/base/session"

    @openerpweb.jsonrequest
    def login(self, req, db, login, password):
        req.session.login('trunk', login, password)
        res = {
            "session_id" : req.session_id,
            "uid": req.session._uid,
        }
        return res

    def modules(self, req):
        # TODO return the list of all modules
        res={}
        res["modules"] = ["base","base_hello"]
        return res

class Menu(openerpweb.Controller):
    _cp_path = "/base/menu"

    @openerpweb.jsonrequest
    def load(self,req):
        m = req.session.model('ir.ui.menu')
        # menus are loaded fully unlike a regular tree view, cause there are
        # less than 512 items
        menu_ids = m.search([])
        menu_items = m.read(menu_ids,['name','sequence','parent_id'])
        menu_root = {'id':False, 'name':'root', 'parent_id':[-1,'']}
        menu_items.append(menu_root)
        # make a tree using parent_id
        for i in menu_items:
            i['children'] = []
        d = dict([(i["id"],i) for i in menu_items])
        for i in menu_items:
            if i['parent_id'] == False:
                pid = False
            else:
                pid = i['parent_id'][0]
            if pid in d:
                d[pid]['children'].append(i)
        # sort by sequence a tree using parent_id
        for i in menu_items:
            i['children'].sort(key = lambda x:x["sequence"])
        res={}
        res['data']=menu_root
        return res

    @openerpweb.jsonrequest
    def action(self,req,menu_id):
        m = req.session.model('ir.values')
        r = m.get('action', 'tree_but_open', [('ir.ui.menu', menu_id)], False, {})
        res={"action":r}
        return res

class DataSet(openerpweb.Controller):
    _cp_path = "/base/dataset"

    @openerpweb.jsonrequest
    def fields(self,req,model):
        return {'fields': req.session.model(model).fields_get(False)}

    @openerpweb.jsonrequest
    def load(self,req,model,domain=[],fields=['id']):
        m = req.session.model(model)
        ids = m.search(domain)
        values = m.read(ids, fields)
        res = {}
        res['ids'] = ids
        res['values'] = values
        return res

class FormView(openerpweb.Controller):
    _cp_path = "/base/formview"
    @openerpweb.jsonrequest
    def load(self,req,model,view_id):
        m = req.session.model(model)
        r = m.fields_view_get(view_id,'form')
        r["arch"]=Xml2Json.convert_to_structure(r["arch"])
        return {'fields_view':r}

class ListView(openerpweb.Controller):
    _cp_path = "/base/listview"
    @openerpweb.jsonrequest
    def load(self,req,model,view_id):
        m = req.session.model(model)
        r = m.fields_view_get(view_id,'tree')
        r["arch"]=Xml2Json.convert_to_structure(r["arch"])
        return {'fields_view':r}

class SearchView(openerpweb.Controller):
    _cp_path = "/base/searchview"
    @openerpweb.jsonrequest
    def load(self,req,model,view_id):
        m = req.session.model(model)
        r = m.fields_view_get(view_id,'search')
        r["arch"]=Xml2Json.convert_to_structure(r["arch"])
        return {'fields_view':r}

class Action(openerpweb.Controller):
    _cp_path = "/base/action"

    @openerpweb.jsonrequest
    def load(self,req,action_id):
        #m = req.session.model('ir.ui.menu')
        res={}
        return res

#
