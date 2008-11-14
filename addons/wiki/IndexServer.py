#!/usr/bin/python

from SimpleXMLRPCServer import SimpleXMLRPCServer
import os
import csv
from config import *
import xmlrpclib
import PyLucene
import threading 

class IndexServer(threading.Thread):
    
    def __init__(self):
        super(IndexServer,self).__init__()
        self.path = os.path.join('/tmp', 'index')
        
    def initIndex(self, database, user, password, new=False):
        self.database = database
        self.user = user
        self.password = password
        self.new = new
        self.writer = None
        
    def open(self):
        if not os.path.exists(self.path):
            os.mkdir(path)
            self.new = True
            
        store = PyLucene.FSDirectory.getDirectory(path, self.new)
        self.writer = PyLucene.IndexWriter(store, PyLucene.StandardAnalyzer(), self.new)
        url = 'http://%s:%s/xmlrpc/object' % (tiny_host, str(tiny_port))
        self.proxy = xmlrpclib.ServerProxy(url);
        return True
        
    def addDocument(self, model, id, data):
        
        doc = PyLucene.Document()
        doc.add(PyLucene.Field("model", model,
                               PyLucene.Field.Store.YES,
                               PyLucene.Field.Index.UN_TOKENIZED))
        indexid=str(id)

        doc.add(PyLucene.Field("id", indexid,
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.UN_TOKENIZED))

        doc.add(PyLucene.Field("contents", data,
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.TOKENIZED))
        self.writer.addDocument(doc)
        
        return True
    
    def doIndex(self, models=None):
        
        self.open()
        
        toIndex = []
        if models is None:
            toIndex = self.proxy.execute(self.database, self.user, self.password, 'ir.model' ,'search', [])
        else:
            toIndex = models
        
        models = self.proxy.execute(self.database, self.user, self.password, 'ir.model' ,'read', toIndex, ['model'])
        for mod in models:
            res_ids = self.proxy.execute(self.database, self.user, self.password, mod['model'], 'search', [])
            
            if str(mod['model']).startswith('ir'):
                continue
            
            if str(mod['model']).startswith('res.currency'):
                continue
            
            print 'creating index for : ', str(mod['model'])
            try:
                res_datas = self.proxy.execute(self.database, self.user, self.password, mod['model'], 'read', res_ids)
            except Exception, e:
                print e
                continue
            
            for res_data in res_datas:
                self.addDocument(mod['model'], res_data['id'], ' '.join(map(str,res_data.values())))
                
        self.new = False
        self.close()
        return True
    
    def reIndex(self, models = None):
        self.new = True
        self.doIndex(models)
        
    def close(self):
        self.writer.close()
        return True
    
    def addRecord(self, model, id, data):
        self.new = False
        self.open()
        doc = PyLucene.Document()
        doc.add(PyLucene.Field("model", model,
                               PyLucene.Field.Store.YES,
                               PyLucene.Field.Index.UN_TOKENIZED))
        indexid=str(id)

        doc.add(PyLucene.Field("id", indexid,
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.UN_TOKENIZED))

        doc.add(PyLucene.Field("contents", data,
                           PyLucene.Field.Store.YES,
                           PyLucene.Field.Index.TOKENIZED))
        self.writer.addDocument(doc)
        self.close()
        return True

    def search(self, keys):
        directory = PyLucene.FSDirectory.getDirectory(self.path, False)
        searcher = PyLucene.IndexSearcher(directory)
        analyzer = PyLucene.StandardAnalyzer()
        
        query = PyLucene.QueryParser("contents", analyzer).parse(keys)
        hits = searcher.search(query)
        count= hits.length()
        result = {}

        for i, doc in hits:
            model = doc.get('model')
            id = doc.get('id')
            
            if result.has_key(model):
                ids = result.get(model)
                ids.append(id)
            else:
                ids = []
                ids.append(id)
                result[model] = ids 
            
        searcher.close()
        
        if result.__len__() <=0 :
            result = False
            
        return result
    
    def run(self):
        server = SimpleXMLRPCServer((index_server,index_port),allow_none=True)
        indexer = IndexServer()
        server.register_instance(indexer, True)
        server.register_function(indexer.initIndex, 'init')
        server.register_function(indexer.open, 'open')
        server.register_function(indexer.addRecord, 'add')
        server.register_function(indexer.doIndex, 'index')
        server.register_function(indexer.reIndex, 'reindex')
        server.register_function(indexer.close, 'close')
        server.register_function(indexer.search, 'search')
        server.register_introspection_functions()
        server.serve_forever()
#end class

server = SimpleXMLRPCServer((index_server,index_port),allow_none=True)
indexer = IndexServer()
server.register_function(indexer.initIndex, 'init')
server.register_function(indexer.open, 'open')
server.register_function(indexer.addRecord, 'add')
server.register_function(indexer.doIndex, 'index')
server.register_function(indexer.reIndex, 'reindex')
server.register_function(indexer.close, 'close')
server.register_function(indexer.search, 'search')
server.register_introspection_functions()
server.register_multicall_functions()
server.serve_forever()
#
#try:
#    print 'Starting Index Server', index_server, index_port
#    server = IndexServer()
#    server.start()
#except Exception , e:
#    print e
