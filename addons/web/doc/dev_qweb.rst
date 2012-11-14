
QWeb
====

QWeb is the template engine used by the OpenERP Web Client. It is a home made engine create by OpenERP developers. There are a few things to note about it:

* Template are rendered in javascript on the client-side, the server does nothing.
* It is an xml template engine, like Facelets_ for example. The source file must be a valid xml.
* Templates are not interpreted. There are compiled to javascript. This makes them a lot faster to render, but sometimes harder to debug.
* Most of the time it is used through the Widget class, but you can also use it directly using *openerp.web.qweb.render()* .

.. _Facelets: http://en.wikipedia.org/wiki/Facelets

Here is a typical QWeb file:

::

    <?xml version="1.0" encoding="UTF-8"?>
    <templates>
        <t t-name="Template1">
            <div>...</div>
        </t>
        <t t-name="Template2">
            <div>...</div>
        </t>
    </templates>

A QWeb file contains multiple templates, they are simply identified by a name.

Here is a sample QWeb template:

::

    <t t-name="UserPage">
        <div>
            <p>Name: <t t-esc="widget.user_name"/></p>
            <p>Password: <input type="text" t-att-value="widget.password"/></p>
            <p t-if="widget.is_admin">This user is an Administrator</p>
            <t t-foreach="widget.roles" t-as="role">
                <p>User has role: <t t-esc="role"/></p>
            </t>
        </div>
    </t>


*widget* is a variable given to the template engine by Widget sub-classes when they decide to render their associated template, it is simply *this*. Here is the corresponding Widget sub-class:

::

    UserPageWidget = openerp.base.Widget.extend({
        template: "UserPage",
        init: function(parent) {
            this._super(parent);
            this.user_name = "Xavier";
            this.password = "lilo";
            this.is_admin = true;
            this.roles = ["Web Developer", "IE Hater", "Steve Jobs Worshiper"];
        },
    });

It could output something like this:

::

    <div>
        <p>Name: Xavier</p>
        <p>Password: <input type="text" value="lilo"/></p>
        <p>This user is an Administrator</p
        <p>User has role: Web Developer</p>
        <p>User has role: IE Hater</p>
        <p>User has role: Steve Jobs Worshiper</p>
    </div>

A QWeb template should always contain one unique root element to be used effectively with the Widget class, here it is a *<div>*. QWeb only react to *<t>* elements or attributes prefixed by *t-*. The *<t>* is simply a null element, it is only used when you need to use a *t-* attribute without outputting an html element at the same time. Here are the effects of the most common QWeb attributes:

* *t-esc* outputs the result of the evaluation of the given javascript expression
* *t-att-ATTR* sets the value of the *ATTR* attribute to the result of the evaluation of the given javascript expression
* *t-if* outputs the element and its content only if the given javascript expression returns true
* *t-foreach* outputs as many times as contained in the list returned by the given javascript expression. For each iteration, a variable with the name defined by *t-as* contains the current element in the list.
