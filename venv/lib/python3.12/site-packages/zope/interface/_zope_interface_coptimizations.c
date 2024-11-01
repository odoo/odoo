/*###########################################################################
 #
 # Copyright (c) 2003 Zope Foundation and Contributors.
 # All Rights Reserved.
 #
 # This software is subject to the provisions of the Zope Public License,
 # Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
 # THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
 # WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 # WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
 # FOR A PARTICULAR PURPOSE.
 #
 ############################################################################*/

#include "Python.h"
#include "structmember.h"

#ifdef __clang__
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunused-parameter"
#pragma clang diagnostic ignored "-Wmissing-field-initializers"
#endif

#define TYPE(O) ((PyTypeObject*)(O))
#define OBJECT(O) ((PyObject*)(O))
#define CLASSIC(O) ((PyClassObject*)(O))
#ifndef Py_TYPE
#define Py_TYPE(o) ((o)->ob_type)
#endif

#define PyNative_FromString PyUnicode_FromString

#define ASSURE_DICT(N)                                                         \
    if (N == NULL) {                                                           \
        N = PyDict_New();                                                      \
        if (N == NULL)                                                         \
            return NULL;                                                       \
    }

/*
 *  Don't use heap-allocated types for Python < 3.11:  the API needed
 *  to find the dynamic module, 'PyType_GetModuleByDef', was added then.
 */
#if PY_VERSION_HEX < 0x030b0000
#define USE_STATIC_TYPES 1
#define USE_HEAP_TYPES 0
#else
#define USE_STATIC_TYPES 0
#define USE_HEAP_TYPES 1
#endif

#define BASETYPE_FLAGS \
    Py_TPFLAGS_DEFAULT | \
    Py_TPFLAGS_BASETYPE | \
    Py_TPFLAGS_HAVE_GC

#if PY_VERSION_HEX >= 0x030c0000
/* Add MANAGED_WEAKREF flag for Python >= 3.12, and don't define
 * the '.tp_weaklistoffset' slot.
 *
 * See: https://docs.python.org/3/c-api/typeobj.html
 *      #c.PyTypeObject.tp_weaklistoffset
 */
#define USE_EXPLICIT_WEAKREFLIST 0
#define WEAKREFTYPE_FLAGS BASETYPE_FLAGS | Py_TPFLAGS_MANAGED_WEAKREF
#else
/* No MANAGED_WEAKREF flag for Python < 3.12, and therefore define
 * the '.tp_weaklistoffset' slot, and the member whose offset it holds.
 *
 * See: https://docs.python.org/3/c-api/typeobj.html
 *      #c.PyTypeObject.tp_weaklistoffset
 */
#define USE_EXPLICIT_WEAKREFLIST 1
#define WEAKREFTYPE_FLAGS BASETYPE_FLAGS
#endif

/* Static strings, used to invoke PyObject_GetAttr (only in hot paths) */
static PyObject *str__class__ = NULL;
static PyObject *str__conform__ = NULL;
static PyObject *str__dict__ = NULL;
static PyObject *str__module__ = NULL;
static PyObject *str__name__ = NULL;
static PyObject *str__providedBy__ = NULL;
static PyObject *str__provides__ = NULL;
static PyObject *str__self__ = NULL;
static PyObject *str_generation = NULL;
static PyObject *str_registry = NULL;
static PyObject *strro = NULL;

/* Static strings, used to invoke PyObject_CallMethodObjArgs */
static PyObject *str_call_conform = NULL;
static PyObject *str_uncached_lookup = NULL;
static PyObject *str_uncached_lookupAll = NULL;
static PyObject *str_uncached_subscriptions = NULL;
static PyObject *strchanged = NULL;
static PyObject *str__adapt__ = NULL;

/* Static strings, used to invoke PyObject_GetItem
 *
 * We cannot use PyDict_GetItemString, because the '__dict__' we get
 * from our types can be a 'types.mappingproxy', which causes a segfault.
 */
static PyObject* str__implemented__;


static int
define_static_strings()
{
    if (str__class__ != NULL) {
        return 0;
    }

#define DEFINE_STATIC_STRING(S)                  \
    if (!(str##S = PyUnicode_FromString(#S)))    \
    return -1

    DEFINE_STATIC_STRING(__class__);
    DEFINE_STATIC_STRING(__conform__);
    DEFINE_STATIC_STRING(__dict__);
    DEFINE_STATIC_STRING(__module__);
    DEFINE_STATIC_STRING(__name__);
    DEFINE_STATIC_STRING(__providedBy__);
    DEFINE_STATIC_STRING(__provides__);
    DEFINE_STATIC_STRING(__self__);
    DEFINE_STATIC_STRING(_generation);
    DEFINE_STATIC_STRING(_registry);
    DEFINE_STATIC_STRING(ro);
    DEFINE_STATIC_STRING(__implemented__);
    DEFINE_STATIC_STRING(_call_conform);
    DEFINE_STATIC_STRING(_uncached_lookup);
    DEFINE_STATIC_STRING(_uncached_lookupAll);
    DEFINE_STATIC_STRING(_uncached_subscriptions);
    DEFINE_STATIC_STRING(changed);
    DEFINE_STATIC_STRING(__adapt__);
#undef DEFINE_STATIC_STRING

    return 0;
}

/* Public module-scope functions, forward-declared here for type methods. */
static PyObject *implementedBy(PyObject* module, PyObject *cls);
static PyObject *getObjectSpecification(PyObject *module, PyObject *ob);
static PyObject *providedBy(PyObject *module, PyObject *ob);

/*
 * Utility functions, forward-declared here for type methods.
 */
static PyObject* _get_module(PyTypeObject *typeobj);
static PyObject* _get_adapter_hooks(PyTypeObject *typeobj);
static PyTypeObject* _get_specification_base_class(PyTypeObject *typeobj);
static PyTypeObject* _get_interface_base_class(PyTypeObject *typeobj);

#if USE_STATIC_TYPES
/*
 *  Global used by static IB__adapt
 */
static PyObject*       adapter_hooks = NULL;

/*
 *  Globals imported from 'zope.interface.declarations'
 */
static int imported_declarations = 0;
static PyObject* BuiltinImplementationSpecifications;
static PyObject* empty;
static PyObject* fallback;
static PyTypeObject *Implements;

/* Import zope.interface.declarations and store results in global statics.
 *
 * Static alternative to '_zic_state_load_declarations' below.
 */
static int
import_declarations(void)
{
    PyObject *declarations, *i;

    declarations = PyImport_ImportModule("zope.interface.declarations");
    if (declarations == NULL) { return -1; }

    BuiltinImplementationSpecifications = PyObject_GetAttrString(
                        declarations, "BuiltinImplementationSpecifications");
    if (BuiltinImplementationSpecifications == NULL) { return -1; }

    empty = PyObject_GetAttrString(declarations, "_empty");
    if (empty == NULL) { return -1; }

    fallback = PyObject_GetAttrString(declarations, "implementedByFallback");
    if (fallback == NULL) { return -1;}

    i = PyObject_GetAttrString(declarations, "Implements");
    if (i == NULL) { return -1; }

    if (! PyType_Check(i)) {
        PyErr_SetString(
            PyExc_TypeError,
            "zope.interface.declarations.Implements is not a type");
        return -1;
    }

    Implements = (PyTypeObject *)i;

    Py_DECREF(declarations);

    imported_declarations = 1;
    return 0;
}

#endif

/*
 *  SpecificationBase class
 */
typedef struct
{
    PyObject_HEAD
    /*
      In the past, these fields were stored in the __dict__
      and were technically allowed to contain any Python object, though
      other type checks would fail or fall back to generic code paths if
      they didn't have the expected type. We preserve that behaviour and don't
      make any assumptions about contents.
    */
    PyObject* _implied;
#if USE_EXPLICIT_WEAKREFLIST
    PyObject* weakreflist;
#endif
    /*
      The remainder aren't used in C code but must be stored here
      to prevent instance layout conflicts.
    */
    PyObject* _dependents;
    PyObject* _bases;
    PyObject* _v_attrs;
    PyObject* __iro__;
    PyObject* __sro__;
} SB;

/*
  We know what the fields are *supposed* to define, but
  they could have anything, so we need to traverse them.
*/
static int
SB_traverse(SB* self, visitproc visit, void* arg)
{
/* Visit our 'tp_type' only on Python >= 3.9, per
 * https://docs.python.org/3/howto/isolating-extensions.html
 * #tp-traverse-in-python-3-8-and-lower
 */
#if USE_HEAP_TYPES && PY_VERSION_HEX > 0x03090000
    Py_VISIT(Py_TYPE(self));
#endif
    Py_VISIT(self->_implied);
    Py_VISIT(self->_dependents);
    Py_VISIT(self->_bases);
    Py_VISIT(self->_v_attrs);
    Py_VISIT(self->__iro__);
    Py_VISIT(self->__sro__);
    return 0;
}

static int
SB_clear(SB* self)
{
    Py_CLEAR(self->_implied);
    Py_CLEAR(self->_dependents);
    Py_CLEAR(self->_bases);
    Py_CLEAR(self->_v_attrs);
    Py_CLEAR(self->__iro__);
    Py_CLEAR(self->__sro__);
    return 0;
}

static void
SB_dealloc(SB* self)
{
    PyObject_GC_UnTrack((PyObject*)self);
    PyObject_ClearWeakRefs(OBJECT(self));
    PyTypeObject* tp = Py_TYPE(self);
    SB_clear(self);
    tp->tp_free(OBJECT(self));
#if USE_HEAP_TYPES
    Py_DECREF(tp);
#endif
}

static char SB_extends__doc__[] =
  "Test whether a specification is or extends another";

static PyObject*
SB_extends(SB* self, PyObject* other)
{
    PyObject* implied;

    implied = self->_implied;
    if (implied == NULL) {
        return NULL;
    }

    if (PyDict_GetItem(implied, other) != NULL)
        Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

static PyObject*
SB__call__(SB* self, PyObject* args, PyObject* kw)
{
    PyObject* spec;

    if (!PyArg_ParseTuple(args, "O", &spec))
        return NULL;
    return SB_extends(self, spec);
}

static char SB_providedBy__doc__[] =
  "Test whether an interface is implemented by the specification";

static PyObject*
SB_providedBy(PyObject* self, PyObject* ob)
{
    PyObject *decl;
    PyObject *item;
    PyObject *module;
    PyTypeObject *specification_base_class;

    module = _get_module(Py_TYPE(self));
    specification_base_class = _get_specification_base_class(Py_TYPE(self));

    decl = providedBy(module, ob);
    if (decl == NULL)
        return NULL;

    if (PyObject_TypeCheck(decl, specification_base_class))
        item = SB_extends((SB*)decl, self);
    else
        /* decl is probably a security proxy.  We have to go the long way
           around.
        */
        item = PyObject_CallFunctionObjArgs(decl, self, NULL);

    Py_DECREF(decl);
    return item;
}

static char SB_implementedBy__doc__[] =
  "Test whether the specification is implemented by a class or factory.\n"
  "Raise TypeError if argument is neither a class nor a callable.";

static PyObject*
SB_implementedBy(PyObject* self, PyObject* cls)
{
    PyObject *decl;
    PyObject *item;
    PyObject *module;
    PyTypeObject *specification_base_class;

    module = _get_module(Py_TYPE(self));
    specification_base_class = _get_specification_base_class(Py_TYPE(self));

    decl = implementedBy(module, cls);
    if (decl == NULL)
        return NULL;

    if (PyObject_TypeCheck(decl, specification_base_class))
        item = SB_extends((SB*)decl, self);
    else
        item = PyObject_CallFunctionObjArgs(decl, self, NULL);

    Py_DECREF(decl);
    return item;
}

static struct PyMethodDef SB_methods[] = {
    { "providedBy",
      (PyCFunction)SB_providedBy,
      METH_O,
      SB_providedBy__doc__ },
    { "implementedBy",
      (PyCFunction)SB_implementedBy,
      METH_O,
      SB_implementedBy__doc__ },
    { "isOrExtends",
      (PyCFunction)SB_extends,
      METH_O,
      SB_extends__doc__ },

    { NULL, NULL } /* sentinel */
};

static PyMemberDef SB_members[] = {
    { "_implied", T_OBJECT_EX, offsetof(SB, _implied), 0, "" },
    { "_dependents", T_OBJECT_EX, offsetof(SB, _dependents), 0, "" },
    { "_bases", T_OBJECT_EX, offsetof(SB, _bases), 0, "" },
    { "_v_attrs", T_OBJECT_EX, offsetof(SB, _v_attrs), 0, "" },
    { "__iro__", T_OBJECT_EX, offsetof(SB, __iro__), 0, "" },
    { "__sro__", T_OBJECT_EX, offsetof(SB, __sro__), 0, "" },
#if USE_EXPLICIT_WEAKREFLIST
    { "__weaklistoffset__", T_PYSSIZET, offsetof(SB, weakreflist), READONLY, "" },
#endif
    { NULL },
};

static char SB__name__[] = "_zope_interface_coptimizations.SpecificationBase";
static char SB__doc__[] = "Base type for Specification objects";

#if USE_STATIC_TYPES

/*
 * Static type: SpecificationBase
 */

static PyTypeObject SB_type_def = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name           = SB__name__,
    .tp_doc            = SB__doc__,
    .tp_basicsize      = sizeof(SB),
    .tp_flags          = WEAKREFTYPE_FLAGS,
    .tp_call           = (ternaryfunc)SB__call__,
    .tp_traverse       = (traverseproc)SB_traverse,
    .tp_clear          = (inquiry)SB_clear,
    .tp_dealloc        = (destructor)SB_dealloc,
#if USE_EXPLICIT_WEAKREFLIST
    .tp_weaklistoffset = offsetof(SB, weakreflist),
#endif
    .tp_methods        = SB_methods,
    .tp_members        = SB_members,
};

#else

/*
 * Heap-based type: SpecificationBase
 */
static PyType_Slot SB_type_slots[] = {
    {Py_tp_doc,         SB__doc__},
    {Py_tp_call,        SB__call__},
    {Py_tp_traverse,    SB_traverse},
    {Py_tp_clear,       SB_clear},
    {Py_tp_dealloc,     SB_dealloc},
    {Py_tp_methods,     SB_methods},
    {Py_tp_members,     SB_members},
    {0,                 NULL}
};

static PyType_Spec SB_type_spec = {
    .name               = SB__name__,
    .basicsize          = sizeof(SB),
    .flags              = WEAKREFTYPE_FLAGS,
    .slots              = SB_type_slots
};

#endif

/*
 *  ObjectSpecificationDescriptor class
 */
#if USE_HEAP_TYPES
static int
OSD_traverse(PyObject* self, visitproc visit, void* arg)
{
    Py_VISIT(Py_TYPE(self));
    return 0;
}

static void
OSD_dealloc(PyObject* self)
{
    PyObject_GC_UnTrack(self);
    PyTypeObject *tp = Py_TYPE(self);
    tp->tp_free(OBJECT(self));
    Py_DECREF(tp);
}
#endif

static PyObject*
OSD_descr_get(PyObject* self, PyObject* inst, PyObject* cls)
{
    PyObject* provides;
    PyObject *module;

    module = _get_module(Py_TYPE(self));

    if (inst == NULL) {
        return getObjectSpecification(module, cls);
    }

    provides = PyObject_GetAttr(inst, str__provides__);
    /* Return __provides__ if we got it, or return NULL and propagate
     * non-AttributeError. */
    if (provides != NULL || !PyErr_ExceptionMatches(PyExc_AttributeError)) {
        return provides;
    }

    PyErr_Clear();

    return implementedBy(module, cls);
}

static char OSD__name__[] = (
    "_zope_interface_coptimizations.ObjectSpecificationDescriptor");
static char OSD__doc__[] = "Object Specification Descriptor";

#if USE_STATIC_TYPES

/*
 * Static type: ObjectSpecificationDescriptor
 */

static PyTypeObject OSD_type_def = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name            = OSD__name__,
    .tp_doc             = OSD__doc__,
    /* No GC for the static version */
    .tp_flags           = Py_TPFLAGS_DEFAULT |
                          Py_TPFLAGS_BASETYPE,
    .tp_descr_get       = (descrgetfunc)OSD_descr_get,
  /*.tp_traverse,       = OSD_traverse},     not reqd for static */
  /*.tp_dealloc,        = OSD_dealloc},      not reqd for static */
};

#else

/*
 * Heap type: ObjectSpecificationDescriptor
 */
static PyType_Slot OSD_type_slots[] = {
    {Py_tp_doc,         OSD__doc__},
    {Py_tp_descr_get,   OSD_descr_get},
    {Py_tp_traverse,    OSD_traverse},
    {Py_tp_dealloc,     OSD_dealloc},
    {0,                 NULL}
};

static PyType_Spec OSD_type_spec = {
    .name               = OSD__name__,
    .basicsize          = 0,
    .flags              = BASETYPE_FLAGS,
    .slots              = OSD_type_slots
};

#endif

/*
 *  ClassProvidesBase class
 */
typedef struct
{
    SB spec;
    /* These members are handled generically, as for SB members. */
    PyObject* _cls;
    PyObject* _implements;
} CPB;

static int
CPB_traverse(CPB* self, visitproc visit, void* arg)
{
    Py_VISIT(self->_cls);
    Py_VISIT(self->_implements);
    return SB_traverse((SB*)self, visit, arg);
}

static int
CPB_clear(CPB* self)
{
    Py_CLEAR(self->_cls);
    Py_CLEAR(self->_implements);
    return SB_clear((SB*)self);
}

static void
CPB_dealloc(CPB* self)
{
    PyObject_GC_UnTrack((PyObject*)self);
    CPB_clear(self);
    SB_dealloc((SB*)self); /* handles decrefing tp */
}

static PyObject*
CPB_descr_get(CPB* self, PyObject* inst, PyObject* cls)
{
    PyObject* implements;

    if (self->_cls == NULL)
        return NULL;

    if (cls == self->_cls) {
        if (inst == NULL) {
            Py_INCREF(self);
            return OBJECT(self);
        }

        implements = self->_implements;
        Py_XINCREF(implements);
        return implements;
    }

    PyErr_SetString(PyExc_AttributeError, "__provides__");
    return NULL;
}

static PyMemberDef CPB_members[] = {
    { "_cls", T_OBJECT_EX, offsetof(CPB, _cls), 0, "Defining class." },
    { "_implements",
      T_OBJECT_EX,
      offsetof(CPB, _implements),
      0,
      "Result of implementedBy." },
    { NULL }
};

static char CPB__name__[] = "_zope_interface_coptimizations.ClassProvidesBase";
static char CPB__doc__[] = "C Base class for ClassProvides";

#if USE_STATIC_TYPES

/*
 * Static type: ClassProvidesBase
 */

static PyTypeObject CPB_type_def = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name            = CPB__name__,
    .tp_doc             = CPB__doc__,
    .tp_base            = &SB_type_def,
    .tp_basicsize       = sizeof(CPB),
    .tp_flags           = BASETYPE_FLAGS,
    .tp_descr_get       = (descrgetfunc)CPB_descr_get,
    .tp_traverse        = (traverseproc)CPB_traverse,
    .tp_clear           = (inquiry)CPB_clear,
    .tp_dealloc         = (destructor)CPB_dealloc,
    .tp_members         = CPB_members,
};

#else

/*
 * Heap type: ClassProvidesBase
 */
static PyType_Slot CPB_type_slots[] = {
    {Py_tp_doc,         CPB__doc__},
    {Py_tp_descr_get,   CPB_descr_get},
    {Py_tp_traverse,    CPB_traverse},
    {Py_tp_clear,       CPB_clear},
    {Py_tp_dealloc,     CPB_dealloc},
    {Py_tp_members,     CPB_members},
    /* tp_base cannot be set as a slot -- pass to PyType_FromModuleAndSpec */
    {0,                 NULL}
};

static PyType_Spec CPB_type_spec = {
    .name               = CPB__name__,
    .basicsize          = sizeof(CPB),
    .flags              = BASETYPE_FLAGS,
    .slots              = CPB_type_slots
};

#endif

/*
 *  InterfaceBase class
 */

typedef struct
{
    SB spec;
    PyObject* __name__;
    PyObject* __module__;
    Py_hash_t _v_cached_hash;
} IB;

static int
IB_traverse(IB* self, visitproc visit, void* arg)
{
    Py_VISIT(self->__name__);
    Py_VISIT(self->__module__);
    return SB_traverse((SB*)self, visit, arg);
}

static int
IB_clear(IB* self)
{
    Py_CLEAR(self->__name__);
    Py_CLEAR(self->__module__);
    return SB_clear((SB*)self);
}

static void
IB_dealloc(IB* self)
{
    PyObject_GC_UnTrack((PyObject*)self);
    IB_clear(self);
    SB_dealloc((SB*)self); /* handles decrefing tp */
}

static int
IB__init__(IB* self, PyObject* args, PyObject* kwargs)
{
    static char* kwlist[] = { "__name__", "__module__", NULL };
    PyObject* module = NULL;
    PyObject* name = NULL;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwargs, "|OO:InterfaceBase.__init__", kwlist, &name, &module)) {
        return -1;
    }
    IB_clear(self);
    self->__module__ = module ? module : Py_None;
    Py_INCREF(self->__module__);
    self->__name__ = name ? name : Py_None;
    Py_INCREF(self->__name__);
    return 0;
}

/*
    def __adapt__(self, obj):
        """Adapt an object to the receiver
        """
        if self.providedBy(obj):
            return obj

        for hook in adapter_hooks:
            adapter = hook(self, obj)
            if adapter is not None:
                return adapter


*/
const char IB__adapt____doc__[] = "Adapt an object to the receiver";

static PyObject*
IB__adapt__(PyObject* self, PyObject* obj)
{
    PyObject *decl;
    PyObject *args;
    PyObject *adapter;
    PyObject *module;
    PyObject *adapter_hooks;
    PyTypeObject *specification_base_class;
    int implements;
    int i;
    int l;

    module = _get_module(Py_TYPE(self));

    decl = providedBy(module, obj);
    if (decl == NULL)
        return NULL;

    specification_base_class = _get_specification_base_class(Py_TYPE(self));

    if (PyObject_TypeCheck(decl, specification_base_class)) {
        PyObject* implied;

        implied = ((SB*)decl)->_implied;
        if (implied == NULL) {
            Py_DECREF(decl);
            return NULL;
        }

        implements = PyDict_GetItem(implied, self) != NULL;
        Py_DECREF(decl);
    } else {
        /* decl is probably a security proxy.  We have to go the long way
           around.
        */
        PyObject* r;
        r = PyObject_CallFunctionObjArgs(decl, self, NULL);
        Py_DECREF(decl);
        if (r == NULL)
            return NULL;
        implements = PyObject_IsTrue(r);
        Py_DECREF(r);
    }

    if (implements) {
        Py_INCREF(obj);
        return obj;
    }

    args = PyTuple_New(2);
    if (args == NULL) { return NULL; }

    Py_INCREF(self);
    PyTuple_SET_ITEM(args, 0, self);

    Py_INCREF(obj);
    PyTuple_SET_ITEM(args, 1, obj);

    adapter_hooks = _get_adapter_hooks(Py_TYPE(self));
    l = PyList_GET_SIZE(adapter_hooks);
    for (i = 0; i < l; i++) {
        adapter = PyObject_CallObject(PyList_GET_ITEM(adapter_hooks, i), args);
        if (adapter == NULL || adapter != Py_None) {
            Py_DECREF(args);
            return adapter;
        }
        Py_DECREF(adapter);
    }

    Py_DECREF(args);

    Py_INCREF(Py_None);
    return Py_None;
}

/*
    def __call__(self, obj, alternate=_marker):
        try:
            conform = obj.__conform__
        except AttributeError: # pylint:disable=bare-except
            conform = None

        if conform is not None:
            adapter = self._call_conform(conform)
            if adapter is not None:
                return adapter

        adapter = self.__adapt__(obj)

        if adapter is not None:
            return adapter
        if alternate is not _marker:
            return alternate
        raise TypeError("Could not adapt", obj, self)

*/
static PyObject*
IB__call__(PyObject* self, PyObject* args, PyObject* kwargs)
{
    PyObject *conform, *obj, *alternate, *adapter;
    static char* kwlist[] = { "obj", "alternate", NULL };
    conform = obj = alternate = adapter = NULL;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwargs, "O|O", kwlist, &obj, &alternate))
        return NULL;

    conform = PyObject_GetAttr(obj, str__conform__);
    if (conform == NULL) {
        if (!PyErr_ExceptionMatches(PyExc_AttributeError)) {
            /* Propagate non-AttributeErrors */
            return NULL;
        }
        PyErr_Clear();

        Py_INCREF(Py_None);
        conform = Py_None;
    }

    if (conform != Py_None) {
        adapter =
          PyObject_CallMethodObjArgs(self, str_call_conform, conform, NULL);
        Py_DECREF(conform);
        if (adapter == NULL || adapter != Py_None)
            return adapter;
        Py_DECREF(adapter);
    } else {
        Py_DECREF(conform);
    }

    /* We differ from the Python code here. For speed, instead of always calling
       self.__adapt__(), we check to see if the type has defined it. Checking in
       the dict for __adapt__ isn't sufficient because there's no cheap way to
       tell if it's the __adapt__ that InterfaceBase itself defines (our type
       will *never* be InterfaceBase, we're always subclassed by
       InterfaceClass). Instead, we cooperate with InterfaceClass in Python to
       set a flag in a new subclass when this is necessary. */
    if (PyDict_GetItemString(self->ob_type->tp_dict, "_CALL_CUSTOM_ADAPT")) {
        /* Doesn't matter what the value is. Simply being present is enough. */
        adapter = PyObject_CallMethodObjArgs(self, str__adapt__, obj, NULL);
    } else {
        adapter = IB__adapt__(self, obj);
    }

    if (adapter == NULL || adapter != Py_None) {
        return adapter;
    }
    Py_DECREF(adapter);

    if (alternate != NULL) {
        Py_INCREF(alternate);
        return alternate;
    }

    adapter = Py_BuildValue("sOO", "Could not adapt", obj, self);
    if (adapter != NULL) {
        PyErr_SetObject(PyExc_TypeError, adapter);
        Py_DECREF(adapter);
    }
    return NULL;
}

static Py_hash_t
IB__hash__(IB* self)
{
    PyObject* tuple;
    if (!self->__module__) {
        PyErr_SetString(PyExc_AttributeError, "__module__");
        return -1;
    }
    if (!self->__name__) {
        PyErr_SetString(PyExc_AttributeError, "__name__");
        return -1;
    }

    if (self->_v_cached_hash) {
        return self->_v_cached_hash;
    }

    tuple = PyTuple_Pack(2, self->__name__, self->__module__);
    if (!tuple) {
        return -1;
    }
    self->_v_cached_hash = PyObject_Hash(tuple);
    Py_CLEAR(tuple);
    return self->_v_cached_hash;
}

static PyObject*
IB_richcompare(IB* self, PyObject* other, int op)
{
    PyObject* othername;
    PyObject* othermod;
    PyObject* oresult;
    PyTypeObject* interface_base_class;
    IB* otherib;
    int result;

    otherib = NULL;
    oresult = othername = othermod = NULL;

    if (OBJECT(self) == other) {
        switch (op) {
            case Py_EQ:
            case Py_LE:
            case Py_GE:
                Py_RETURN_TRUE;
                break;
            case Py_NE:
                Py_RETURN_FALSE;
        }
    }

    if (other == Py_None) {
        switch (op) {
            case Py_LT:
            case Py_LE:
            case Py_NE:
                Py_RETURN_TRUE;
            default:
                Py_RETURN_FALSE;
        }
    }

    interface_base_class = _get_interface_base_class(Py_TYPE(self));
    if (interface_base_class == NULL) {
        oresult = Py_NotImplemented;
        goto cleanup;
    }

    if (PyObject_TypeCheck(other, interface_base_class)) {
        // This branch borrows references. No need to clean
        // up if otherib is not null.
        otherib = (IB*)other;
        othername = otherib->__name__;
        othermod = otherib->__module__;
    } else {
        othername = PyObject_GetAttr(other, str__name__);
        if (othername) {
            othermod = PyObject_GetAttr(other, str__module__);
        }
        if (!othername || !othermod) {
            if (PyErr_Occurred() &&
                PyErr_ExceptionMatches(PyExc_AttributeError)) {
                PyErr_Clear();
                oresult = Py_NotImplemented;
            }
            goto cleanup;
        }
    }
#if 0
// This is the simple, straightforward version of what Python does.
    PyObject* pt1 = PyTuple_Pack(2, self->__name__, self->__module__);
    PyObject* pt2 = PyTuple_Pack(2, othername, othermod);
    oresult = PyObject_RichCompare(pt1, pt2, op);
#endif

    // tuple comparison is decided by the first non-equal element.
    result = PyObject_RichCompareBool(self->__name__, othername, Py_EQ);
    if (result == 0) {
        result = PyObject_RichCompareBool(self->__name__, othername, op);
    } else if (result == 1) {
        result = PyObject_RichCompareBool(self->__module__, othermod, op);
    }
    // If either comparison failed, we have an error set.
    // Leave oresult NULL so we raise it.
    if (result == -1) {
        goto cleanup;
    }

    oresult = result ? Py_True : Py_False;

cleanup:
    Py_XINCREF(oresult);

    if (!otherib) {
        Py_XDECREF(othername);
        Py_XDECREF(othermod);
    }
    return oresult;
}

static PyMemberDef IB_members[] = {
    { "__name__", T_OBJECT_EX, offsetof(IB, __name__), 0, "" },
    // The redundancy between __module__ and __ibmodule__ is because
    // __module__ is often shadowed by subclasses.
    { "__module__", T_OBJECT_EX, offsetof(IB, __module__), READONLY, "" },
    { "__ibmodule__", T_OBJECT_EX, offsetof(IB, __module__), 0, "" },
    { NULL }
};

static struct PyMethodDef IB_methods[] = {
    { "__adapt__", (PyCFunction)IB__adapt__, METH_O, IB__adapt____doc__},
    { NULL, NULL } /* sentinel */
};

static char IB__name__[] ="_zope_interface_coptimizations.InterfaceBase";
static char IB__doc__[] = (
    "Interface base type providing __call__ and __adapt__"
);

#if USE_STATIC_TYPES

/*
 * Static type: InterfaceBase
 */

static PyTypeObject IB_type_def = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name            = IB__name__,
    .tp_doc             = IB__doc__,
    .tp_base            = &SB_type_def,
    .tp_basicsize       = sizeof(IB),
    .tp_flags           = BASETYPE_FLAGS,
    .tp_init            = (initproc)IB__init__,
    .tp_hash            = (hashfunc)IB__hash__,
    .tp_richcompare     = (richcmpfunc)IB_richcompare,
    .tp_call            = (ternaryfunc)IB__call__,
    .tp_traverse        = (traverseproc)IB_traverse,
    .tp_clear           = (inquiry)IB_clear,
    .tp_dealloc         = (destructor)IB_dealloc,
    .tp_methods         = IB_methods,
    .tp_members         = IB_members,
};

#else

/*
 * Heap type: InterfaceBase
 */
static PyType_Slot IB_type_slots[] = {
    {Py_tp_doc,         IB__doc__},
    {Py_tp_init,        IB__init__},
    {Py_tp_hash,        IB__hash__},
    {Py_tp_richcompare, IB_richcompare},
    {Py_tp_call,        IB__call__},
    {Py_tp_traverse,    IB_traverse},
    {Py_tp_clear,       IB_clear},
    {Py_tp_dealloc,     IB_dealloc},
    {Py_tp_methods,     IB_methods},
    {Py_tp_members,     IB_members},
    /* tp_base cannot be set as a slot -- pass to PyType_FromModuleAndSpec */
    {0,                   NULL}
};

static PyType_Spec IB_type_spec = {
    .name               = IB__name__,
    .basicsize          = sizeof(IB),
    .flags              = BASETYPE_FLAGS,
    .slots              = IB_type_slots
};

#endif

/*
 *  LookupBase class
 */
typedef struct
{
    PyObject_HEAD
    PyObject* _cache;
    PyObject* _mcache;
    PyObject* _scache;
} LB;

static int
LB_traverse(LB* self, visitproc visit, void* arg)
{
/* Visit our 'tp_type' only on Python >= 3.9, per
 * https://docs.python.org/3/howto/isolating-extensions.html
 * #tp-traverse-in-python-3-8-and-lower
 */
#if USE_HEAP_TYPES && PY_VERSION_HEX > 0x03090000
    Py_VISIT(Py_TYPE(self));
#endif
    Py_VISIT(self->_cache);
    Py_VISIT(self->_mcache);
    Py_VISIT(self->_scache);
    return 0;
}

static int
LB_clear(LB* self)
{
    Py_CLEAR(self->_cache);
    Py_CLEAR(self->_mcache);
    Py_CLEAR(self->_scache);
    return 0;
}

static void
LB_dealloc(LB* self)
{
    PyObject_GC_UnTrack((PyObject*)self);
    PyTypeObject* tp = Py_TYPE(self);
    LB_clear(self);
    tp->tp_free((PyObject*)self);
#if USE_HEAP_TYPES
    Py_DECREF(tp);
#endif
}

/*
    def changed(self, ignored=None):
        self._cache.clear()
        self._mcache.clear()
        self._scache.clear()
*/
static PyObject*
LB_changed(LB* self, PyObject* ignored)
{
    LB_clear(self);
    Py_INCREF(Py_None);
    return Py_None;
}

/*
    def _getcache(self, provided, name):
        cache = self._cache.get(provided)
        if cache is None:
            cache = {}
            self._cache[provided] = cache
        if name:
            c = cache.get(name)
            if c is None:
                c = {}
                cache[name] = c
            cache = c
        return cache
*/
static PyObject*
_subcache(PyObject* cache, PyObject* key)
{
    PyObject* subcache;

    subcache = PyDict_GetItem(cache, key);
    if (subcache == NULL) {
        int status;

        subcache = PyDict_New();
        if (subcache == NULL)
            return NULL;
        status = PyDict_SetItem(cache, key, subcache);
        Py_DECREF(subcache);
        if (status < 0)
            return NULL;
    }

    return subcache;
}

static PyObject*
_getcache(LB* self, PyObject* provided, PyObject* name)
{
    PyObject* cache;

    ASSURE_DICT(self->_cache);

    cache = _subcache(self->_cache, provided);
    if (cache == NULL)
        return NULL;

    if (name != NULL && PyObject_IsTrue(name))
        cache = _subcache(cache, name);

    return cache;
}

/*
    def lookup(self, required, provided, name=u'', default=None):
        cache = self._getcache(provided, name)
        if len(required) == 1:
            result = cache.get(required[0], _not_in_mapping)
        else:
            result = cache.get(tuple(required), _not_in_mapping)

        if result is _not_in_mapping:
            result = self._uncached_lookup(required, provided, name)
            if len(required) == 1:
                cache[required[0]] = result
            else:
                cache[tuple(required)] = result

        if result is None:
            return default

        return result
*/

static PyObject*
_lookup(LB* self,
        PyObject* required,
        PyObject* provided,
        PyObject* name,
        PyObject* default_)
{
    PyObject *result, *key, *cache;
    result = key = cache = NULL;
    if (name && !PyUnicode_Check(name)) {
        PyErr_SetString(PyExc_ValueError, "name is not a string");
        return NULL;
    }

    /* If `required` is a lazy sequence, it could have arbitrary side-effects,
       such as clearing our caches. So we must not retrieve the cache until
       after resolving it. */
    required = PySequence_Tuple(required);
    if (required == NULL)
        return NULL;

    cache = _getcache(self, provided, name);
    if (cache == NULL)
        return NULL;

    if (PyTuple_GET_SIZE(required) == 1)
        key = PyTuple_GET_ITEM(required, 0);
    else
        key = required;

    result = PyDict_GetItem(cache, key);
    if (result == NULL) {
        int status;

        result = PyObject_CallMethodObjArgs(
          OBJECT(self), str_uncached_lookup, required, provided, name, NULL);
        if (result == NULL) {
            Py_DECREF(required);
            return NULL;
        }
        status = PyDict_SetItem(cache, key, result);
        Py_DECREF(required);
        if (status < 0) {
            Py_DECREF(result);
            return NULL;
        }
    } else {
        Py_INCREF(result);
        Py_DECREF(required);
    }

    if (result == Py_None && default_ != NULL) {
        Py_DECREF(Py_None);
        Py_INCREF(default_);
        return default_;
    }

    return result;
}

static PyObject*
LB_lookup(LB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "required", "provided", "name", "default", NULL };
    PyObject *required, *provided, *name = NULL, *default_ = NULL;

    if (!PyArg_ParseTupleAndKeywords(args,
                                     kwds,
                                     "OO|OO:LookupBase.lookup",
                                     kwlist,
                                     &required,
                                     &provided,
                                     &name,
                                     &default_))
        return NULL;

    return _lookup(self, required, provided, name, default_);
}

/*
    def lookup1(self, required, provided, name=u'', default=None):
        cache = self._getcache(provided, name)
        result = cache.get(required, _not_in_mapping)
        if result is _not_in_mapping:
            return self.lookup((required, ), provided, name, default)

        if result is None:
            return default

        return result
*/
static PyObject*
_lookup1(LB* self,
         PyObject* required,
         PyObject* provided,
         PyObject* name,
         PyObject* default_)
{
    PyObject *result, *cache;

    if (name && !PyUnicode_Check(name)) {
        PyErr_SetString(PyExc_ValueError, "name is not a string");
        return NULL;
    }

    cache = _getcache(self, provided, name);
    if (cache == NULL)
        return NULL;

    result = PyDict_GetItem(cache, required);
    if (result == NULL) {
        PyObject* tup;

        tup = PyTuple_New(1);
        if (tup == NULL)
            return NULL;
        Py_INCREF(required);
        PyTuple_SET_ITEM(tup, 0, required);
        result = _lookup(self, tup, provided, name, default_);
        Py_DECREF(tup);
    } else {
        if (result == Py_None && default_ != NULL) {
            result = default_;
        }
        Py_INCREF(result);
    }

    return result;
}
static PyObject*
LB_lookup1(LB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "required", "provided", "name", "default", NULL };
    PyObject *required, *provided, *name = NULL, *default_ = NULL;

    if (!PyArg_ParseTupleAndKeywords(args,
                                     kwds,
                                     "OO|OO:LookupBase.lookup1",
                                     kwlist,
                                     &required,
                                     &provided,
                                     &name,
                                     &default_))
        return NULL;

    return _lookup1(self, required, provided, name, default_);
}

/*
    def adapter_hook(self, provided, object, name=u'', default=None):
        required = providedBy(object)
        cache = self._getcache(provided, name)
        factory = cache.get(required, _not_in_mapping)
        if factory is _not_in_mapping:
            factory = self.lookup((required, ), provided, name)

        if factory is not None:
            if isinstance(object, super):
                object = object.__self__
            result = factory(object)
            if result is not None:
                return result

        return default
*/
static PyObject*
_adapter_hook(LB* self,
              PyObject* provided,
              PyObject* object,
              PyObject* name,
              PyObject* default_)
{
    PyObject *required;
    PyObject *factory;
    PyObject *result;
    PyObject *module;

    module = _get_module(Py_TYPE(self));

    if (name && !PyUnicode_Check(name)) {
        PyErr_SetString(PyExc_ValueError, "name is not a string");
        return NULL;
    }

    required = providedBy(module, object);
    if (required == NULL)
        return NULL;

    factory = _lookup1(self, required, provided, name, Py_None);
    Py_DECREF(required);
    if (factory == NULL)
        return NULL;

    if (factory != Py_None) {
        if (PyObject_TypeCheck(object, &PySuper_Type)) {
            PyObject* self = PyObject_GetAttr(object, str__self__);
            if (self == NULL) {
                Py_DECREF(factory);
                return NULL;
            }
            // Borrow the reference to self
            Py_DECREF(self);
            object = self;
        }
        result = PyObject_CallFunctionObjArgs(factory, object, NULL);
        Py_DECREF(factory);
        if (result == NULL || result != Py_None)
            return result;
    } else
        result = factory; /* None */

    if (default_ == NULL || default_ == result) /* No default specified, */
        return result; /* Return None.  result is owned None */

    Py_DECREF(result);
    Py_INCREF(default_);

    return default_;
}

static PyObject*
LB_adapter_hook(LB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "provided", "object", "name", "default", NULL };
    PyObject *object, *provided, *name = NULL, *default_ = NULL;

    if (!PyArg_ParseTupleAndKeywords(args,
                                     kwds,
                                     "OO|OO:LookupBase.adapter_hook",
                                     kwlist,
                                     &provided,
                                     &object,
                                     &name,
                                     &default_))
        return NULL;

    return _adapter_hook(self, provided, object, name, default_);
}

static PyObject*
LB_queryAdapter(LB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "object", "provided", "name", "default", NULL };
    PyObject *object, *provided, *name = NULL, *default_ = NULL;

    if (!PyArg_ParseTupleAndKeywords(args,
                                     kwds,
                                     "OO|OO:LookupBase.queryAdapter",
                                     kwlist,
                                     &object,
                                     &provided,
                                     &name,
                                     &default_))
        return NULL;

    return _adapter_hook(self, provided, object, name, default_);
}

/*
    def lookupAll(self, required, provided):
        cache = self._mcache.get(provided)
        if cache is None:
            cache = {}
            self._mcache[provided] = cache

        required = tuple(required)
        result = cache.get(required, _not_in_mapping)
        if result is _not_in_mapping:
            result = self._uncached_lookupAll(required, provided)
            cache[required] = result

        return result
*/
static PyObject*
_lookupAll(LB* self, PyObject* required, PyObject* provided)
{
    PyObject *cache, *result;

    /* resolve before getting cache. See note in _lookup. */
    required = PySequence_Tuple(required);
    if (required == NULL)
        return NULL;

    ASSURE_DICT(self->_mcache);

    cache = _subcache(self->_mcache, provided);
    if (cache == NULL)
        return NULL;

    result = PyDict_GetItem(cache, required);
    if (result == NULL) {
        int status;

        result = PyObject_CallMethodObjArgs(
          OBJECT(self), str_uncached_lookupAll, required, provided, NULL);
        if (result == NULL) {
            Py_DECREF(required);
            return NULL;
        }
        status = PyDict_SetItem(cache, required, result);
        Py_DECREF(required);
        if (status < 0) {
            Py_DECREF(result);
            return NULL;
        }
    } else {
        Py_INCREF(result);
        Py_DECREF(required);
    }

    return result;
}

static PyObject*
LB_lookupAll(LB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "required", "provided", NULL };
    PyObject *required, *provided;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "OO:LookupBase.lookupAll", kwlist, &required, &provided))
        return NULL;

    return _lookupAll(self, required, provided);
}

/*
    def subscriptions(self, required, provided):
        cache = self._scache.get(provided)
        if cache is None:
            cache = {}
            self._scache[provided] = cache

        required = tuple(required)
        result = cache.get(required, _not_in_mapping)
        if result is _not_in_mapping:
            result = self._uncached_subscriptions(required, provided)
            cache[required] = result

        return result
*/
static PyObject*
_subscriptions(LB* self, PyObject* required, PyObject* provided)
{
    PyObject *cache, *result;

    /* resolve before getting cache. See note in _lookup. */
    required = PySequence_Tuple(required);
    if (required == NULL)
        return NULL;

    ASSURE_DICT(self->_scache);

    cache = _subcache(self->_scache, provided);
    if (cache == NULL)
        return NULL;

    result = PyDict_GetItem(cache, required);
    if (result == NULL) {
        int status;

        result = PyObject_CallMethodObjArgs(
          OBJECT(self), str_uncached_subscriptions, required, provided, NULL);
        if (result == NULL) {
            Py_DECREF(required);
            return NULL;
        }
        status = PyDict_SetItem(cache, required, result);
        Py_DECREF(required);
        if (status < 0) {
            Py_DECREF(result);
            return NULL;
        }
    } else {
        Py_INCREF(result);
        Py_DECREF(required);
    }

    return result;
}

static PyObject*
LB_subscriptions(LB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "required", "provided", NULL };
    PyObject *required, *provided;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "OO", kwlist, &required, &provided))
        return NULL;

    return _subscriptions(self, required, provided);
}

static struct PyMethodDef LB_methods[] = {
    { "changed", (PyCFunction)LB_changed, METH_O, "" },
    { "lookup", (PyCFunction)LB_lookup, METH_KEYWORDS | METH_VARARGS, "" },
    { "lookup1",
      (PyCFunction)LB_lookup1,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { "queryAdapter",
      (PyCFunction)LB_queryAdapter,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { "adapter_hook",
      (PyCFunction)LB_adapter_hook,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { "lookupAll",
      (PyCFunction)LB_lookupAll,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { "subscriptions",
      (PyCFunction)LB_subscriptions,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { NULL, NULL } /* sentinel */
};

static char LB__name__[] = "_zope_interface_coptimizations.LookupBase";
static char LB__doc__[] = "Base class for adapter registries";


#if USE_STATIC_TYPES

/*
 * Static type: LookupBase
 */

static PyTypeObject LB_type_def = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name            = LB__name__,
    .tp_doc             = LB__doc__,
    .tp_basicsize       = sizeof(LB),
    .tp_flags           = BASETYPE_FLAGS,
    .tp_traverse        = (traverseproc)LB_traverse,
    .tp_clear           = (inquiry)LB_clear,
    .tp_dealloc         = (destructor)&LB_dealloc,
    .tp_methods         = LB_methods,
};

#else

/*
 * Heap type: LookupBase
 */
static PyType_Slot LB_type_slots[] = {
    {Py_tp_doc,         LB__doc__},
    {Py_tp_traverse,    LB_traverse},
    {Py_tp_clear,       LB_clear},
    {Py_tp_dealloc,     LB_dealloc},
    {Py_tp_methods,     LB_methods},
    {0,                 NULL}
};

static PyType_Spec LB_type_spec = {
    .name               = LB__name__,
    .basicsize          = sizeof(LB),
    .flags              = BASETYPE_FLAGS,
    .slots              = LB_type_slots
};

#endif

typedef struct
{
    LB          lookup;
    PyObject*   _verify_ro;
    PyObject*   _verify_generations;
} VB;

static int
VB_traverse(VB* self, visitproc visit, void* arg)
{
    Py_VISIT(self->_verify_ro);
    Py_VISIT(self->_verify_generations);
    return LB_traverse((LB*)self, visit, arg);
}

static int
VB_clear(VB* self)
{
    Py_CLEAR(self->_verify_generations);
    Py_CLEAR(self->_verify_ro);
    return LB_clear((LB*)self);
}

static void
VB_dealloc(VB* self)
{
    PyObject_GC_UnTrack((PyObject*)self);
    PyTypeObject *tp = Py_TYPE(self);
    VB_clear(self);
    tp->tp_free((PyObject*)self);
#if USE_HEAP_TYPES
    Py_DECREF(tp);
#endif
}

/*
    def changed(self, originally_changed):
        super(VerifyingBasePy, self).changed(originally_changed)
        self._verify_ro = self._registry.ro[1:]
        self._verify_generations = [r._generation for r in self._verify_ro]
*/
static PyObject*
_generations_tuple(PyObject* ro)
{
    int i, l;
    PyObject* generations;

    l = PyTuple_GET_SIZE(ro);
    generations = PyTuple_New(l);
    for (i = 0; i < l; i++) {
        PyObject* generation;

        generation = PyObject_GetAttr(PyTuple_GET_ITEM(ro, i), str_generation);
        if (generation == NULL) {
            Py_DECREF(generations);
            return NULL;
        }
        PyTuple_SET_ITEM(generations, i, generation);
    }

    return generations;
}
static PyObject*
verify_changed(VB* self, PyObject* ignored)
{
    PyObject *t, *ro;

    VB_clear(self);

    t = PyObject_GetAttr(OBJECT(self), str_registry);
    if (t == NULL)
        return NULL;

    ro = PyObject_GetAttr(t, strro);
    Py_DECREF(t);
    if (ro == NULL)
        return NULL;

    t = PyObject_CallFunctionObjArgs(OBJECT(&PyTuple_Type), ro, NULL);
    Py_DECREF(ro);
    if (t == NULL)
        return NULL;

    ro = PyTuple_GetSlice(t, 1, PyTuple_GET_SIZE(t));
    Py_DECREF(t);
    if (ro == NULL)
        return NULL;

    self->_verify_generations = _generations_tuple(ro);
    if (self->_verify_generations == NULL) {
        Py_DECREF(ro);
        return NULL;
    }

    self->_verify_ro = ro;

    Py_INCREF(Py_None);
    return Py_None;
}

/*
    def _verify(self):
        if ([r._generation for r in self._verify_ro]
            != self._verify_generations):
            self.changed(None)
*/
static int
_verify(VB* self)
{
    PyObject* changed_result;

    if (self->_verify_ro != NULL && self->_verify_generations != NULL) {
        PyObject* generations;
        int changed;

        generations = _generations_tuple(self->_verify_ro);
        if (generations == NULL)
            return -1;

        changed = PyObject_RichCompareBool(
          self->_verify_generations, generations, Py_NE);
        Py_DECREF(generations);
        if (changed == -1)
            return -1;

        if (changed == 0)
            return 0;
    }

    changed_result =
      PyObject_CallMethodObjArgs(OBJECT(self), strchanged, Py_None, NULL);
    if (changed_result == NULL)
        return -1;

    Py_DECREF(changed_result);
    return 0;
}

static PyObject*
VB_lookup(VB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "required", "provided", "name", "default", NULL };
    PyObject *required, *provided, *name = NULL, *default_ = NULL;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "OO|OO", kwlist, &required, &provided, &name, &default_))
        return NULL;

    if (_verify(self) < 0)
        return NULL;

    return _lookup((LB*)self, required, provided, name, default_);
}

static PyObject*
VB_lookup1(VB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "required", "provided", "name", "default", NULL };
    PyObject *required, *provided, *name = NULL, *default_ = NULL;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "OO|OO", kwlist, &required, &provided, &name, &default_))
        return NULL;

    if (_verify(self) < 0)
        return NULL;

    return _lookup1((LB*)self, required, provided, name, default_);
}

static PyObject*
VB_adapter_hook(VB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "provided", "object", "name", "default", NULL };
    PyObject *object, *provided, *name = NULL, *default_ = NULL;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "OO|OO", kwlist, &provided, &object, &name, &default_))
        return NULL;

    if (_verify(self) < 0)
        return NULL;

    return _adapter_hook((LB*)self, provided, object, name, default_);
}

static PyObject*
VB_queryAdapter(VB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "object", "provided", "name", "default", NULL };
    PyObject *object, *provided, *name = NULL, *default_ = NULL;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "OO|OO", kwlist, &object, &provided, &name, &default_))
        return NULL;

    if (_verify(self) < 0)
        return NULL;

    return _adapter_hook((LB*)self, provided, object, name, default_);
}

static PyObject*
VB_lookupAll(VB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "required", "provided", NULL };
    PyObject *required, *provided;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "OO", kwlist, &required, &provided))
        return NULL;

    if (_verify(self) < 0)
        return NULL;

    return _lookupAll((LB*)self, required, provided);
}

static PyObject*
VB_subscriptions(VB* self, PyObject* args, PyObject* kwds)
{
    static char* kwlist[] = { "required", "provided", NULL };
    PyObject *required, *provided;

    if (!PyArg_ParseTupleAndKeywords(
          args, kwds, "OO", kwlist, &required, &provided))
        return NULL;

    if (_verify(self) < 0)
        return NULL;

    return _subscriptions((LB*)self, required, provided);
}

static struct PyMethodDef VB_methods[] = {
    { "changed", (PyCFunction)verify_changed, METH_O, "" },
    { "lookup",
      (PyCFunction)VB_lookup,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { "lookup1",
      (PyCFunction)VB_lookup1,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { "queryAdapter",
      (PyCFunction)VB_queryAdapter,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { "adapter_hook",
      (PyCFunction)VB_adapter_hook,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { "lookupAll",
      (PyCFunction)VB_lookupAll,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { "subscriptions",
      (PyCFunction)VB_subscriptions,
      METH_KEYWORDS | METH_VARARGS,
      "" },
    { NULL, NULL } /* sentinel */
};

static char VB__name__[] = "_zope_interface_coptimizations.VerifyingBase";
static char VB__doc__[] = "Base class for verifying adapter registries.";

#if USE_STATIC_TYPES

/*
 * Static type: VerifyingBase
 */

static PyTypeObject VB_type_def = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name            = VB__name__,
    .tp_doc             = VB__doc__,
    .tp_base            = &LB_type_def,
    .tp_basicsize       = sizeof(VB),
    .tp_flags           = BASETYPE_FLAGS,
    .tp_traverse        = (traverseproc)VB_traverse,
    .tp_clear           = (inquiry)VB_clear,
    .tp_dealloc         = (destructor)&VB_dealloc,
    .tp_methods         = VB_methods,
};


#else

/*
 * Heap type: VerifyingBase
 */
static PyType_Slot VB_type_slots[] = {
    {Py_tp_doc,         VB__doc__},
    {Py_tp_traverse,    VB_traverse},
    {Py_tp_clear,       VB_clear},
    {Py_tp_dealloc,     VB_dealloc},
    {Py_tp_methods,     VB_methods},
    /* tp_base cannot be set as a slot -- pass to PyType_FromModuleAndSpec */
    {0,                 NULL}
};

static PyType_Spec VB_type_spec = {
    .name               = VB__name__,
    .basicsize          = sizeof(VB),
    .flags              = BASETYPE_FLAGS,
    .slots              = VB_type_slots
};

#endif


/*
 * Module state struct:  holds all data formerly kept as static globals.
 */
typedef struct
{
    /* our globals (exposed to Python) */
    PyTypeObject*   specification_base_class;
    PyTypeObject*   object_specification_descriptor_class;
    PyTypeObject*   class_provides_base_class;
    PyTypeObject*   interface_base_class;
    PyTypeObject*   lookup_base_class;
    PyTypeObject*   verifying_base_class;
    PyObject*       adapter_hooks;
    /* members imported from 'zope.interface.declarations'
     */
    PyObject*       empty;
    PyObject*       fallback;
    PyObject*       builtin_impl_specs;
    PyTypeObject*   implements_class;
    /* flag:  have we imported the next set of members yet from
     * 'zope.interface.declarations?
     */
    int             decl_imported;
} _zic_module_state;

/*
 *  Macro to speed lookup of state members
 */
#define _zic_state(o) ((_zic_module_state*)PyModule_GetState(o))

static _zic_module_state*
_zic_state_init(PyObject* module)
{
    _zic_module_state* rec = _zic_state(module);

    rec->specification_base_class = NULL;
    rec->object_specification_descriptor_class = NULL;
    rec->class_provides_base_class = NULL;
    rec->interface_base_class = NULL;
    rec->lookup_base_class = NULL;
    rec->verifying_base_class = NULL;
    rec->adapter_hooks = NULL;

    rec->builtin_impl_specs = NULL;
    rec->empty = NULL;
    rec->fallback = NULL;
    rec->implements_class = NULL;
    rec->decl_imported = 0;

    return rec;
}

static int
_zic_state_traverse(PyObject* module, visitproc visit, void* arg)
{
    _zic_module_state* rec = _zic_state(module);

    Py_VISIT(rec->specification_base_class);
    Py_VISIT(rec->object_specification_descriptor_class);
    Py_VISIT(rec->class_provides_base_class);
    Py_VISIT(rec->interface_base_class);
    Py_VISIT(rec->lookup_base_class);
    Py_VISIT(rec->verifying_base_class);
    Py_VISIT(rec->adapter_hooks);

    Py_VISIT(rec->builtin_impl_specs);
    Py_VISIT(rec->empty);
    Py_VISIT(rec->fallback);
    Py_VISIT(rec->implements_class);

    return 0;
}

static int
_zic_state_clear(PyObject* module)
{
    _zic_module_state* rec = _zic_state(module);

    Py_CLEAR(rec->specification_base_class);
    Py_CLEAR(rec->object_specification_descriptor_class);
    Py_CLEAR(rec->class_provides_base_class);
    Py_CLEAR(rec->interface_base_class);
    Py_CLEAR(rec->lookup_base_class);
    Py_CLEAR(rec->verifying_base_class);
    Py_CLEAR(rec->adapter_hooks);

    Py_CLEAR(rec->builtin_impl_specs);
    Py_CLEAR(rec->empty);
    Py_CLEAR(rec->fallback);
    Py_CLEAR(rec->implements_class);

    return 0;
}

#if USE_HEAP_TYPES
/* Import zope.interface.declarations and store results in module state.
 *
 * Dynamic alternative to 'import_declarations' above.
 */
static _zic_module_state*
_zic_state_load_declarations(PyObject* module)
{
    PyObject* declarations;
    PyObject* builtin_impl_specs;
    PyObject* empty;
    PyObject* fallback;
    PyObject* implements;

    _zic_module_state* rec = _zic_state(module);

    if (!rec->decl_imported) {
        declarations = PyImport_ImportModule("zope.interface.declarations");
        if (declarations == NULL) {
            return NULL;
        }

        builtin_impl_specs = PyObject_GetAttrString(
          declarations, "BuiltinImplementationSpecifications");
        if (builtin_impl_specs == NULL) {
            return NULL;
        }

        empty = PyObject_GetAttrString(declarations, "_empty");
        if (empty == NULL) {
            return NULL;
        }

        fallback =
          PyObject_GetAttrString(declarations, "implementedByFallback");
        if (fallback == NULL) {
            return NULL;
        }

        implements = PyObject_GetAttrString(declarations, "Implements");
        if (implements == NULL) {
            return NULL;
        }

        if (!PyType_Check(implements)) {
            PyErr_SetString(
              PyExc_TypeError,
              "zope.interface.declarations.Implements is not a type");
            return NULL;
        }

        Py_DECREF(declarations);

        rec->builtin_impl_specs = builtin_impl_specs;
        rec->empty = empty;
        rec->fallback = fallback;
        rec->implements_class = (PyTypeObject*)implements;
        rec->decl_imported = 1;
    }
    return rec;
}

#endif

/*
 *  Provide access to the current module given the type.
 */

static struct PyModuleDef _zic_module_def;

static PyObject*
_get_module(PyTypeObject *typeobj)
{
#if USE_STATIC_TYPES
    return (PyObject*)&_zic_module_def;
#else
    if (PyType_Check(typeobj)) {
        /* Only added in Python 3.11 */
        return PyType_GetModuleByDef(typeobj, &_zic_module_def);
    }

    PyErr_SetString(PyExc_TypeError, "_get_module: called w/ non-type");
    return NULL;
#endif
}

/*
 * Fetch the adapter hooks for the current type's module.
 */
static PyObject*
_get_adapter_hooks(PyTypeObject *typeobj)
{
#if USE_STATIC_TYPES
    return adapter_hooks;
#else
    PyObject* module;
    _zic_module_state* rec;

    module = _get_module(typeobj);
    if (module == NULL) { return NULL; }

    rec = _zic_state(module);
    return rec->adapter_hooks;
#endif
}

/*
 * Fetch the 'SpecificationBase' class for the current type's module.
 */
static PyTypeObject*
_get_specification_base_class(PyTypeObject *typeobj)
{
#if USE_STATIC_TYPES
    return &SB_type_def;
#else
    PyObject* module;
    _zic_module_state* rec;

    module = _get_module(typeobj);
    if (module == NULL) { return NULL; }

    rec = _zic_state(module);
    return rec->specification_base_class;
#endif
}

/*
 * Fetch the 'InterfaceBase' class for the current type's module.
 */
static PyTypeObject*
_get_interface_base_class(PyTypeObject *typeobj)
{
#if USE_STATIC_TYPES
    return &IB_type_def;
#else
    PyObject* module;
    _zic_module_state* rec;

    module = _get_module(typeobj);
    if (module == NULL) { return NULL; }

    rec = _zic_state(module);
    return rec->interface_base_class;
#endif
}

static PyObject*
implementedByFallback(PyObject* module, PyObject* cls)
{
#if USE_STATIC_TYPES
    if (imported_declarations == 0 && import_declarations() < 0) {
        return NULL;
    }
    /* now use static 'fallback' */
#else
    PyObject* fallback;

    _zic_module_state* rec = _zic_state_load_declarations(module);
    if (rec == NULL) { return NULL; }

    fallback = rec->fallback;
#endif

    return PyObject_CallFunctionObjArgs(fallback, cls, NULL);
}

static char implementedBy___doc__[] =
  ("Interfaces implemented by a class or factory.\n"
   "Raises TypeError if argument is neither a class nor a callable.");

static PyObject*
implementedBy(PyObject* module, PyObject* cls)
{
    /* Fast retrieval of implements spec, if possible, to optimize
       common case.  Use fallback code if we get stuck.
    */
    PyObject *dict = NULL;
    PyObject *spec;
    PyTypeObject *implements_class;
    PyObject *builtin_impl_specs;

#if USE_STATIC_TYPES
    if (imported_declarations == 0 && import_declarations() < 0) {
        return NULL;
    }

    implements_class = Implements;
    builtin_impl_specs = BuiltinImplementationSpecifications;
#else
    _zic_module_state* rec = _zic_state_load_declarations(module);
    if (rec == NULL) { return NULL; }

    implements_class = rec->implements_class;
    builtin_impl_specs = rec->builtin_impl_specs;
#endif

    if (PyObject_TypeCheck(cls, &PySuper_Type)) {
        // Let merging be handled by Python.
        return implementedByFallback(module, cls);
    }

    if (PyType_Check(cls)) {
        dict = TYPE(cls)->tp_dict;
        Py_XINCREF(dict);
    }

    if (dict == NULL)
        dict = PyObject_GetAttr(cls, str__dict__);

    if (dict == NULL) {
        /* Probably a security proxied class, use more expensive fallback code
         */
        PyErr_Clear();
        return implementedByFallback(module, cls);
    }

    spec = PyObject_GetItem(dict, str__implemented__);
    Py_DECREF(dict);
    if (spec) {

        if (PyObject_TypeCheck(spec, implements_class))
            return spec;

        /* Old-style declaration, use more expensive fallback code */
        Py_DECREF(spec);
        return implementedByFallback(module, cls);
    }

    PyErr_Clear();

    /* Maybe we have a builtin */
    spec = PyDict_GetItem(builtin_impl_specs, cls);
    if (spec != NULL) {
        Py_INCREF(spec);
        return spec;
    }

    /* We're stuck, use fallback */
    return implementedByFallback(module, cls);
}

static char getObjectSpecification___doc__[] =
  ("Get an object's interfaces (internal api)");

static PyObject*
getObjectSpecification(PyObject* module, PyObject* ob)
{
    PyObject *cls;
    PyObject *result;
    PyTypeObject *specification_base_class;
    PyObject *empty_;

#if USE_STATIC_TYPES
    specification_base_class = &SB_type_def;

    if (imported_declarations == 0 && import_declarations() < 0) {
        return NULL;
    }
    empty_ = empty;  /* global from import */

#else
    _zic_module_state* rec = _zic_state_load_declarations(module);
    if (rec == NULL) { return NULL; }

    specification_base_class = rec->specification_base_class;
    empty_ = rec->empty;
#endif

    result = PyObject_GetAttr(ob, str__provides__);
    if (!result) {
        if (!PyErr_ExceptionMatches(PyExc_AttributeError)) {
            /* Propagate non AttributeError exceptions. */
            return NULL;
        }
        PyErr_Clear();
    } else {
        int is_instance = -1;
        is_instance =
          PyObject_IsInstance(result, OBJECT(specification_base_class));
        if (is_instance < 0) {
            /* Propagate all errors */
            return NULL;
        }
        if (is_instance) {
            return result;
        }
    }

    /* We do a getattr here so as not to be defeated by proxies */
    cls = PyObject_GetAttr(ob, str__class__);
    if (cls == NULL) {
        if (!PyErr_ExceptionMatches(PyExc_AttributeError)) {
            /* Propagate non-AttributeErrors */
            return NULL;
        }
        PyErr_Clear();

        Py_INCREF(empty_);
        return empty_;
    }
    result = implementedBy(module, cls);
    Py_DECREF(cls);

    return result;
}

static char providedBy___doc__[] = ("Get an object's interfaces");

static PyObject*
providedBy(PyObject* module, PyObject* ob)
{
    PyObject *result = NULL;
    PyObject *cls;
    PyObject *cp;
    PyTypeObject *specification_base_class;
    int is_instance = -1;

    is_instance = PyObject_IsInstance(ob, (PyObject*)&PySuper_Type);
    if (is_instance < 0) {
        if (!PyErr_ExceptionMatches(PyExc_AttributeError)) {
            /* Propagate non-AttributeErrors */
            return NULL;
        }
        PyErr_Clear();
    }
    if (is_instance) {
        return implementedBy(module, ob);
    }

    result = PyObject_GetAttr(ob, str__providedBy__);

    if (result == NULL) {
        if (!PyErr_ExceptionMatches(PyExc_AttributeError)) {
            return NULL;
        }

        PyErr_Clear();
        return getObjectSpecification(module, ob);
    }

    /* We want to make sure we have a spec. We can't do a type check
       because we may have a proxy, so we'll just try to get the
       only attribute.
    */
#if USE_STATIC_TYPES
    specification_base_class = &SB_type_def;
#else
    _zic_module_state* rec = _zic_state(module);
    specification_base_class = rec->specification_base_class;
#endif
    if (PyObject_TypeCheck(result, specification_base_class) ||
        PyObject_HasAttrString(result, "extends"))
        return result;

    /*
      The object's class doesn't understand descriptors.
      Sigh. We need to get an object descriptor, but we have to be
      careful.  We want to use the instance's __provides__,l if
      there is one, but only if it didn't come from the class.
    */
    Py_DECREF(result);

    cls = PyObject_GetAttr(ob, str__class__);
    if (cls == NULL)
        return NULL;

    result = PyObject_GetAttr(ob, str__provides__);
    if (result == NULL) {
        /* No __provides__, so just fall back to implementedBy */
        PyErr_Clear();
        result = implementedBy(module, cls);
        Py_DECREF(cls);
        return result;
    }

    cp = PyObject_GetAttr(cls, str__provides__);
    if (cp == NULL) {
        /* The the class has no provides, assume we're done: */
        PyErr_Clear();
        Py_DECREF(cls);
        return result;
    }

    if (cp == result) {
        /*
          Oops, we got the provides from the class. This means
          the object doesn't have it's own. We should use implementedBy
        */
        Py_DECREF(result);
        result = implementedBy(module, cls);
    }

    Py_DECREF(cls);
    Py_DECREF(cp);

    return result;
}

static struct PyMethodDef _zic_module_methods[] = {
    { "implementedBy",
      (PyCFunction)implementedBy,
      METH_O,
      implementedBy___doc__ },
    { "getObjectSpecification",
      (PyCFunction)getObjectSpecification,
      METH_O,
      getObjectSpecification___doc__ },
    { "providedBy", (PyCFunction)providedBy, METH_O, providedBy___doc__ },

    { NULL, (PyCFunction)NULL, 0, NULL } /* sentinel */
};


/* Handler for the 'execute' phase of multi-phase initialization
 *
 * See: https://docs.python.org/3/c-api/module.html#multi-phase-initialization
 * and: https://peps.python.org/pep-0489/#module-execution-phase
 */
static int
_zic_module_exec(PyObject* module)
{
    _zic_module_state* rec = _zic_state_init(module);

    rec->adapter_hooks = PyList_New(0);
    if (rec->adapter_hooks == NULL)
        return -1;
    Py_INCREF(rec->adapter_hooks);

#if USE_STATIC_TYPES

    /* Initialize static global */
    adapter_hooks = rec->adapter_hooks;

    /* Initialize types: */
    SB_type_def.tp_new = PyBaseObject_Type.tp_new;
    if (PyType_Ready(&SB_type_def) < 0) { return -1; }
    Py_INCREF(&SB_type_def);
    rec->specification_base_class = &SB_type_def;

    OSD_type_def.tp_new = PyBaseObject_Type.tp_new;
    if (PyType_Ready(&OSD_type_def) < 0) { return -1; }
    Py_INCREF(&OSD_type_def);
    rec->object_specification_descriptor_class = &OSD_type_def;

    CPB_type_def.tp_new = PyBaseObject_Type.tp_new;
    if (PyType_Ready(&CPB_type_def) < 0) { return -1; }
    Py_INCREF(&CPB_type_def);
    rec->class_provides_base_class = &CPB_type_def;

    IB_type_def.tp_new = PyBaseObject_Type.tp_new;
    if (PyType_Ready(&IB_type_def) < 0) { return -1; }
    Py_INCREF(&IB_type_def);
    rec->interface_base_class = &IB_type_def;

    LB_type_def.tp_new = PyBaseObject_Type.tp_new;
    if (PyType_Ready(&LB_type_def) < 0) { return -1; }
    Py_INCREF(&LB_type_def);
    rec->lookup_base_class = &LB_type_def;

    VB_type_def.tp_new = PyBaseObject_Type.tp_new;
    if (PyType_Ready(&VB_type_def) < 0) { return -1; }
    Py_INCREF(&VB_type_def);
    rec->verifying_base_class = &VB_type_def;

#else

    PyObject *sb_class;
    PyObject *osd_class;
    PyObject *cpb_class;
    PyObject *ib_class;
    PyObject *lb_class;
    PyObject *vb_class;

    /* Initialize types:
     */
    sb_class = PyType_FromModuleAndSpec(module, &SB_type_spec, NULL);
    if (sb_class == NULL) { return -1; }
    Py_INCREF(sb_class);
    rec->specification_base_class = TYPE(sb_class);

    osd_class = PyType_FromModuleAndSpec(module, &OSD_type_spec, NULL);
    if (osd_class == NULL) { return -1; }
    Py_INCREF(osd_class);
    rec->object_specification_descriptor_class = TYPE(osd_class);

    cpb_class = PyType_FromModuleAndSpec(module, &CPB_type_spec, sb_class);
    if (cpb_class == NULL) { return -1; }
    Py_INCREF(cpb_class);
    rec->class_provides_base_class = TYPE(cpb_class);

    ib_class = PyType_FromModuleAndSpec(module, &IB_type_spec, sb_class);
    if (ib_class == NULL) { return -1; }
    Py_INCREF(ib_class);
    rec->interface_base_class = TYPE(ib_class);

    lb_class = PyType_FromModuleAndSpec(module, &LB_type_spec, NULL);
    if (lb_class == NULL) { return -1; }
    Py_INCREF(lb_class);
    rec->lookup_base_class = TYPE(lb_class);

    vb_class = PyType_FromModuleAndSpec(module, &VB_type_spec, lb_class);
    if (vb_class == NULL) { return -1; }
    Py_INCREF(vb_class);
    rec->verifying_base_class = TYPE(vb_class);

#endif

    /* Add types to our dict FBO python;  also the adapter hooks */
    if (PyModule_AddObject(module,
        "SpecificationBase", OBJECT(rec->specification_base_class)) < 0)
        return -1;

    if (PyModule_AddObject(module,
        "ObjectSpecificationDescriptor",
        OBJECT(rec->object_specification_descriptor_class)) <
        0)
        return -1;

    if (PyModule_AddObject(module,
        "ClassProvidesBase", OBJECT(rec->class_provides_base_class)) < 0)
        return -1;

    if (PyModule_AddObject(module,
        "InterfaceBase", OBJECT(rec->interface_base_class)) < 0)
        return -1;

    if (PyModule_AddObject(module,
        "LookupBase", OBJECT(rec->lookup_base_class)) < 0)
        return -1;

    if (PyModule_AddObject(module,
        "VerifyingBase", OBJECT(rec->verifying_base_class)) < 0)
        return -1;

    if (PyModule_AddObject(module, "adapter_hooks", rec->adapter_hooks) < 0)
        return -1;

    return 0;
}


/* Slot definitions for multi-phase initialization
 *
 * See: https://docs.python.org/3/c-api/module.html#multi-phase-initialization
 * and: https://peps.python.org/pep-0489
 */
static PyModuleDef_Slot _zic_module_slots[] = {
    {Py_mod_exec,       _zic_module_exec},
    {0,                 NULL}
};

static char _zic_module__doc__[] = "C optimizations for zope.interface\n\n";

static struct PyModuleDef _zic_module_def = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_zope_interface_coptimizations",
    .m_doc = _zic_module__doc__,
    .m_size = sizeof(_zic_module_state),
    .m_methods = _zic_module_methods,
    .m_slots=_zic_module_slots,
    .m_traverse = _zic_state_traverse,
    .m_clear = _zic_state_clear,
};

static PyObject*
init(void)
{
    if (define_static_strings() < 0) { return NULL; }

    return PyModuleDef_Init(&_zic_module_def);
}

PyMODINIT_FUNC
PyInit__zope_interface_coptimizations(void)
{
    return init();
}

#ifdef __clang__
#pragma clang diagnostic pop
#endif
