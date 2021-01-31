# -*- coding: utf-8 -*-

""" Classes for dealing with Odoo modules
"""
import erppeek
import json
from json import JSONEncoder

class OdooField(object):
    """ A class for dealing with fields defined in an Odoo model
    """
    def __init__(self, field_name, field_type):
        if not isinstance(field_name, str):
            raise TypeError('String expected, received {0}'.format(
                type(field_name)))
        if not isinstance(field_type, str):
            raise TypeError('String expected, received {0}'.format(
                type(field_type)))
        self.name = field_name
        self.type = field_type

    def get_name(self):
        """ Get the name of the field
        :return: Field name
        """
        return self.name

    def get_type(self):
        """ Get the type of the field
        :return: Field type
        """
        return self.type

class OdooRelation(object):
    """ A class for dealing with relations between Odoo models
    """
    def __init__(self, name, multiplicity, model):
        if not isinstance(name, str):
            raise TypeError('String expected, received {0}'.format(
                type(name)))
        if not isinstance(multiplicity, str):
            raise TypeError('String expected, received {0}'.format(
                type(multiplicity)))
        if not isinstance(model, str):
            raise TypeError('String expected, received {0}'.format(
                type(model)))
        self.name = name
        self.type = multiplicity
        self.model = model

    def get_name(self):
        """ Get the name of the relation
        :return: Relation name
        """
        return self.name

    def get_type(self):
        """ Get the multiplicity of the relation
        :return: Multiplicity of relation
        """
        return self.type

    def get_model(self):
        """ Get the model of the relation
        :return: Relation model
        """
        return self.model

class OdooClass(object):
    """ A class for dealing with odoo models
    """
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError('String expected, received {0}'.format(
                type(name)))
        self.name = name
        self.fields = []
        self.relations = []

    def get_name(self):
        """ Get the name of the class
        :return: Class name
        """
        return self.name

    def get_fields(self):
        """ Get the fields of the class
        :return: Class fields
        """
        return self.fields

    def get_relations(self):
        """ Get the relations of the class
        :return: Class relations
        """
        return self.relations

    def add_field(self, field_name, field_type):
        """ Add a field to the model
        :param field: The field object to add
        :return:
        """
        self.fields.append(OdooField(field_name, field_type))

    def add_relation(self, rel_name, rel_type, rel_model):
        """ Add a relation to the model
        :param relation: The relation object to add
        :return:
        """
        self.relations.append(OdooRelation(rel_name, rel_type, rel_model))

class CustomEncoder(JSONEncoder):
    """ Custom JSONEncoder for dealing with Odoo model data so JSON uses the
    underlying dictionary for the Odoo class
    """
    def default(self, o):
        return o.__dict__

class OdooModelCollection(object):
    """ A class for connecting to an Odoo instance with ERPPeek and getting the
    models from instance. Offers a method to convert the collection to JSON
    """
    def __init__(self, model_filter=None, server='http://localhost:8069',
                 db='default_db',
                 user='admin',
                 password='admin'):
        try:
            self.client = erppeek.Client(server=server,
                                         db=db,
                                         user=user,
                                         password=password)
        except:
            raise RuntimeError('Error connecting to {0} on {1} '
                               'using credentials {2}:{3}'.format(db,
                                                                  server,
                                                                  user,
                                                                  password))
        self.classes = []
        self.relation_models = []
        self.model_filter = model_filter

        print ('Obtaining model list...')
        models = self.client.models()
        models = {models[key]._name: models[key] for key in models.keys()}

        # Filter out not wanted models
        if self.model_filter:
            models = {k: models[k] for k in models.keys() if
                      self.model_filter in k}

        # Build model structure
        for model in models.keys():
            oclass = OdooClass(model)
            fields = models[model].fields()
            for key in fields.keys():
                field_type = fields[key]['type']
                if field_type in ['many2one', 'many2many', 'one2many']:
                    relation_model = fields[key]['relation']
                    oclass.add_relation(key, field_type, relation_model)
                    if relation_model not in self.relation_models and \
                            relation_model not in models.keys():
                        self.relation_models.append(relation_model)
                else:
                    oclass.add_field(key, field_type)
            self.classes.append(oclass)

        for model in self.relation_models:
            oclass = OdooClass(model)
            self.classes.append(oclass)

    def convert_collection_to_json(self):
        """ Method for converting a collection of Odoo models to a JSON format
        :return: JSON representation of Odoo collection
        """
        return json.dumps(self.classes, cls=CustomEncoder)

    def get_classes(self):
        """ Get a list of classes in Odoo Model Collection
        :return: list of Odoo Model Classes
        """
        return self.classes

    def get_relation_models(self):
        """ Get a list of relation models in Odoo Model Collection
        :return: list of Odoo Model Relations
        """
        return self.relation_models
