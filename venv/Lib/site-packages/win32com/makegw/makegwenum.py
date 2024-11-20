"""Utility file for generating PyIEnum support.

This is almost a 'template' file.  It simplay contains almost full
C++ source code for PyIEnum* support, and the Python code simply
substitutes the appropriate interface name.

This module is notmally not used directly - the @makegw@ module
automatically calls this.
"""

#
# INTERNAL FUNCTIONS
#
#


def is_interface_enum(enumtype):
    return not (enumtype[0].isupper() and enumtype[2].isupper())


def _write_enumifc_cpp(f, interface):
    enumtype = interface.name[5:]
    if is_interface_enum(enumtype):
        # Assume an interface.
        enum_interface = "I" + enumtype[:-1]
        converter = "PyObject *ob = PyCom_PyObjectFromIUnknown(rgVar[i], IID_{enum_interface}, FALSE);".format(
            **locals()
        )
        arraydeclare = (
            "{enum_interface} **rgVar = new {enum_interface} *[celt];".format(
                **locals()
            )
        )
    else:
        # Enum of a simple structure
        converter = "PyObject *ob = PyCom_PyObjectFrom{enumtype}(&rgVar[i]);".format(
            **locals()
        )
        arraydeclare = "{enumtype} *rgVar = new {enumtype}[celt];".format(**locals())

    f.write(
        """
// ---------------------------------------------------
//
// Interface Implementation

PyIEnum{enumtype}::PyIEnum{enumtype}(IUnknown *pdisp):
    PyIUnknown(pdisp)
{{
    ob_type = &type;
}}

PyIEnum{enumtype}::~PyIEnum{enumtype}()
{{
}}

/* static */ IEnum{enumtype} *PyIEnum{enumtype}::GetI(PyObject *self)
{{
    return (IEnum{enumtype} *)PyIUnknown::GetI(self);
}}

// @pymethod object|PyIEnum{enumtype}|Next|Retrieves a specified number of items in the enumeration sequence.
PyObject *PyIEnum{enumtype}::Next(PyObject *self, PyObject *args)
{{
    long celt = 1;
    // @pyparm int|num|1|Number of items to retrieve.
    if ( !PyArg_ParseTuple(args, "|l:Next", &celt) )
        return NULL;

    IEnum{enumtype} *pIE{enumtype} = GetI(self);
    if ( pIE{enumtype} == NULL )
        return NULL;

    {arraydeclare}
    if ( rgVar == NULL ) {{
        PyErr_SetString(PyExc_MemoryError, "allocating result {enumtype}s");
        return NULL;
    }}

    int i;
/*    for ( i = celt; i--; )
        // *** possibly init each structure element???
*/

    ULONG celtFetched = 0;
    PY_INTERFACE_PRECALL;
    HRESULT hr = pIE{enumtype}->Next(celt, rgVar, &celtFetched);
    PY_INTERFACE_POSTCALL;
    if (  HRESULT_CODE(hr) != ERROR_NO_MORE_ITEMS && FAILED(hr) )
    {{
        delete [] rgVar;
        return PyCom_BuildPyException(hr,pIE{enumtype}, IID_IE{enumtype});
    }}

    PyObject *result = PyTuple_New(celtFetched);
    if ( result != NULL )
    {{
        for ( i = celtFetched; i--; )
        {{
            {converter}
            if ( ob == NULL )
            {{
                Py_DECREF(result);
                result = NULL;
                break;
            }}
            PyTuple_SET_ITEM(result, i, ob);
        }}
    }}

/*    for ( i = celtFetched; i--; )
        // *** possibly cleanup each structure element???
*/
    delete [] rgVar;
    return result;
}}

// @pymethod |PyIEnum{enumtype}|Skip|Skips over the next specified elementes.
PyObject *PyIEnum{enumtype}::Skip(PyObject *self, PyObject *args)
{{
    long celt;
    if ( !PyArg_ParseTuple(args, "l:Skip", &celt) )
        return NULL;

    IEnum{enumtype} *pIE{enumtype} = GetI(self);
    if ( pIE{enumtype} == NULL )
        return NULL;

    PY_INTERFACE_PRECALL;
    HRESULT hr = pIE{enumtype}->Skip(celt);
    PY_INTERFACE_POSTCALL;
    if ( FAILED(hr) )
        return PyCom_BuildPyException(hr, pIE{enumtype}, IID_IE{enumtype});

    Py_INCREF(Py_None);
    return Py_None;
}}

// @pymethod |PyIEnum{enumtype}|Reset|Resets the enumeration sequence to the beginning.
PyObject *PyIEnum{enumtype}::Reset(PyObject *self, PyObject *args)
{{
    if ( !PyArg_ParseTuple(args, ":Reset") )
        return NULL;

    IEnum{enumtype} *pIE{enumtype} = GetI(self);
    if ( pIE{enumtype} == NULL )
        return NULL;

    PY_INTERFACE_PRECALL;
    HRESULT hr = pIE{enumtype}->Reset();
    PY_INTERFACE_POSTCALL;
    if ( FAILED(hr) )
        return PyCom_BuildPyException(hr, pIE{enumtype}, IID_IE{enumtype});

    Py_INCREF(Py_None);
    return Py_None;
}}

// @pymethod <o PyIEnum{enumtype}>|PyIEnum{enumtype}|Clone|Creates another enumerator that contains the same enumeration state as the current one
PyObject *PyIEnum{enumtype}::Clone(PyObject *self, PyObject *args)
{{
    if ( !PyArg_ParseTuple(args, ":Clone") )
        return NULL;

    IEnum{enumtype} *pIE{enumtype} = GetI(self);
    if ( pIE{enumtype} == NULL )
        return NULL;

    IEnum{enumtype} *pClone;
    PY_INTERFACE_PRECALL;
    HRESULT hr = pIE{enumtype}->Clone(&pClone);
    PY_INTERFACE_POSTCALL;
    if ( FAILED(hr) )
        return PyCom_BuildPyException(hr, pIE{enumtype}, IID_IE{enumtype});

    return PyCom_PyObjectFromIUnknown(pClone, IID_IEnum{enumtype}, FALSE);
}}

// @object PyIEnum{enumtype}|A Python interface to IEnum{enumtype}
static struct PyMethodDef PyIEnum{enumtype}_methods[] =
{{
    {{ "Next", PyIEnum{enumtype}::Next, 1 }},   // @pymeth Next|Retrieves a specified number of items in the enumeration sequence.
    {{ "Skip", PyIEnum{enumtype}::Skip, 1 }},   // @pymeth Skip|Skips over the next specified elementes.
    {{ "Reset", PyIEnum{enumtype}::Reset, 1 }}, // @pymeth Reset|Resets the enumeration sequence to the beginning.
    {{ "Clone", PyIEnum{enumtype}::Clone, 1 }}, // @pymeth Clone|Creates another enumerator that contains the same enumeration state as the current one.
    {{ NULL }}
}};

PyComEnumTypeObject PyIEnum{enumtype}::type("PyIEnum{enumtype}",
        &PyIUnknown::type,
        sizeof(PyIEnum{enumtype}),
        PyIEnum{enumtype}_methods,
        GET_PYCOM_CTOR(PyIEnum{enumtype}));
""".format(
            **locals()
        )
    )


def _write_enumgw_cpp(f, interface):
    enumtype = interface.name[5:]
    if is_interface_enum(enumtype):
        # Assume an interface.
        enum_interface = "I" + enumtype[:-1]
        converter = "if ( !PyCom_InterfaceFromPyObject(ob, IID_{enum_interface}, (void **)&rgVar[i], FALSE) )".format(
            **locals()
        )
        argdeclare = "{enum_interface} __RPC_FAR * __RPC_FAR *rgVar".format(**locals())
    else:
        argdeclare = "{enumtype} __RPC_FAR *rgVar".format(**locals())
        converter = "if ( !PyCom_PyObjectAs{enumtype}(ob, &rgVar[i]) )".format(
            **locals()
        )
    f.write(
        """
// ---------------------------------------------------
//
// Gateway Implementation

// Std delegation
STDMETHODIMP_(ULONG) PyGEnum{enumtype}::AddRef(void) {{return PyGatewayBase::AddRef();}}
STDMETHODIMP_(ULONG) PyGEnum{enumtype}::Release(void) {{return PyGatewayBase::Release();}}
STDMETHODIMP PyGEnum{enumtype}::QueryInterface(REFIID iid, void ** obj) {{return PyGatewayBase::QueryInterface(iid, obj);}}
STDMETHODIMP PyGEnum{enumtype}::GetTypeInfoCount(UINT FAR* pctInfo) {{return PyGatewayBase::GetTypeInfoCount(pctInfo);}}
STDMETHODIMP PyGEnum{enumtype}::GetTypeInfo(UINT itinfo, LCID lcid, ITypeInfo FAR* FAR* pptInfo) {{return PyGatewayBase::GetTypeInfo(itinfo, lcid, pptInfo);}}
STDMETHODIMP PyGEnum{enumtype}::GetIDsOfNames(REFIID refiid, OLECHAR FAR* FAR* rgszNames, UINT cNames, LCID lcid, DISPID FAR* rgdispid) {{return PyGatewayBase::GetIDsOfNames( refiid, rgszNames, cNames, lcid, rgdispid);}}
STDMETHODIMP PyGEnum{enumtype}::Invoke(DISPID dispid, REFIID riid, LCID lcid, WORD wFlags, DISPPARAMS FAR* params, VARIANT FAR* pVarResult, EXCEPINFO FAR* pexcepinfo, UINT FAR* puArgErr) {{return PyGatewayBase::Invoke( dispid, riid, lcid, wFlags, params, pVarResult, pexcepinfo, puArgErr);}}

STDMETHODIMP PyGEnum{enumtype}::Next(
            /* [in] */ ULONG celt,
            /* [length_is][size_is][out] */ {argdeclare},
            /* [out] */ ULONG __RPC_FAR *pCeltFetched)
{{
    PY_GATEWAY_METHOD;
    PyObject *result;
    HRESULT hr = InvokeViaPolicy("Next", &result, "i", celt);
    if ( FAILED(hr) )
        return hr;

    if ( !PySequence_Check(result) )
        goto error;
    int len;
    len = PyObject_Length(result);
    if ( len == -1 )
        goto error;
    if ( len > (int)celt)
        len = celt;

    if ( pCeltFetched )
        *pCeltFetched = len;

    int i;
    for ( i = 0; i < len; ++i )
    {{
        PyObject *ob = PySequence_GetItem(result, i);
        if ( ob == NULL )
            goto error;

        {converter}
        {{
            Py_DECREF(result);
            return PyCom_SetCOMErrorFromPyException(IID_IEnum{enumtype});
        }}
    }}

    Py_DECREF(result);

    return len < (int)celt ? S_FALSE : S_OK;

  error:
    PyErr_Clear(); // just in case
    Py_DECREF(result);
    return PyCom_HandleIEnumNoSequence(IID_IEnum{enumtype});
}}

STDMETHODIMP PyGEnum{enumtype}::Skip(
            /* [in] */ ULONG celt)
{{
    PY_GATEWAY_METHOD;
    return InvokeViaPolicy("Skip", NULL, "i", celt);
}}

STDMETHODIMP PyGEnum{enumtype}::Reset(void)
{{
    PY_GATEWAY_METHOD;
    return InvokeViaPolicy("Reset");
}}

STDMETHODIMP PyGEnum{enumtype}::Clone(
            /* [out] */ IEnum{enumtype} __RPC_FAR *__RPC_FAR *ppEnum)
{{
    PY_GATEWAY_METHOD;
    PyObject * result;
    HRESULT hr = InvokeViaPolicy("Clone", &result);
    if ( FAILED(hr) )
        return hr;

    /*
    ** Make sure we have the right kind of object: we should have some kind
    ** of IUnknown subclass wrapped into a PyIUnknown instance.
    */
    if ( !PyIBase::is_object(result, &PyIUnknown::type) )
    {{
        /* the wrong kind of object was returned to us */
        Py_DECREF(result);
        return PyCom_SetCOMErrorFromSimple(E_FAIL, IID_IEnum{enumtype});
    }}

    /*
    ** Get the IUnknown out of the thing. note that the Python ob maintains
    ** a reference, so we don't have to explicitly AddRef() here.
    */
    IUnknown *punk = ((PyIUnknown *)result)->m_obj;
    if ( !punk )
    {{
        /* damn. the object was released. */
        Py_DECREF(result);
        return PyCom_SetCOMErrorFromSimple(E_FAIL, IID_IEnum{enumtype});
    }}

    /*
    ** Get the interface we want. note it is returned with a refcount.
    ** This QI is actually going to instantiate a PyGEnum{enumtype}.
    */
    hr = punk->QueryInterface(IID_IEnum{enumtype}, (LPVOID *)ppEnum);

    /* done with the result; this DECREF is also for <punk> */
    Py_DECREF(result);

    return PyCom_CheckIEnumNextResult(hr, IID_IEnum{enumtype});
}}
""".format(
            **locals()
        )
    )
