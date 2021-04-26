# Point of Sale UI Reference

Odoo Point of Sale UI (POS UI) is a single page application written using the
OWL Framework.

## Loading POS Data

### The Basics

For the POS UI to properly function, backend data is initially loaded. The entry
point is the `load_pos_data` in the model `pos.session`. This method is the
caller of all the registered `loader` methods. `loader` methods are responsible
in populating the objects that will be sent by `load_pos_data` to properly
instantiate the POS UI.

A `loader` method is just a method in `pos.session` model but it is decorated
using the `loader` decorator. The `loader` decorator requires the name of the
model to be loaded and optionally, the fields of the model to load -- not
providing a list of fields means all fields are loaded.

Each `loader` method is passed an argument called `lcontext` which is
instantiated in `load_pos_data` for each time a `loader` method is called. `lcontext`
has the following fields: `data`, `sorted_ids`, `contents`, `model`, `fields`.

**`data`** : is a dict containing the loaded models. It maps the model name to the
dict of loaded records keyed by id.

```py
{
    'product.product': {
        1: {
            'display_name': 'sandwich',
            ...
        },
        2: {
            ...
        },
        ...
    },
    'res.partner': {
        10: {
            'name': 'Demo',
            ...
        },
        ...
    },
    'pos.session': {
        5: {
            'config_id': 1,
            ...
        },
    }
    ...
}
```

**`sorted_ids`** : is a dict containing the ids of the loaded records. It maps the
model name to the list of ids in the order that the records are queried.

```py
{
    'product.product': [1, 2, ...],
    'res.partner': [10, ...],
}
```

**`contents`** : is part of the `data` object. It is the dict of records
corresponding to the model referred in the decorator. So if the `loader` method
is decorated with `@loader('product.product')`, then `contents` will contain the
`product.product` dict keyed by id.

```py
{
    1: {
        'display_name': 'sandwich',
        ...
    },
    2: {
        ...
    }
}
```

**`model`** : is the model referred in the decorator.

```py
'product.product'
```

**`fields`** : contains the list of field names.

```py
['display_name', 'price', ...]
```

And since each `loader` method is defined in `pos.session` model, the `self`
argument refers to the `pos.session` record being opened.

### Example

Let's take the loader method of `product.product` as an example:

```py
    @loader('product.product', [<list of field names>]) #1
    def _load_product_product(self, lcontext):  #2
        order = "sequence,default_code,name" #3
        domain = self._get_product_product_domain() #4
        records = self.env[lcontext.model].with_context(display_default_code=False).search(domain, order=order).read(lcontext.fields, load=False) #5
        for record in records: #6
            lcontext.contents[record["id"]] = record #7
        lcontext.sorted_ids[lcontext.model] = [record["id"] for record in records] #8

    def _get_product_product_domain(self):
        # calculate domain
        return domain
```

At `#1`, the method is decorated using the `loader` decorator, and we passed the
model name and list of field names.

At `#2`, we declare the method that will actually be called by `load_pos_data` to
load the data need by the POS UI. Notice that its arguments are `self` and
`lcontext`. As already mentioned, `self` is the `pos.session` record and
`lcontext` is the context object passed to each loader method.

From `#3` to `#8`, here we defined what the loader method does.

At `#3`, we just defined the order variable that will be passed when querying `product.product`.

At `#4`, we compute the domain to use for querying `product.product`.

At `#5`, we perform the search and read using the `lcontext.model` which is
`'product.product'` and using the domain and order defined at #4 and #3
respectively. We also passed the `lcontext.fields` which qualifies the fields to
be read by the orm.

At `#6` and `#7`, we loop thru each record and we save each to `lcontext.contents`
using the record id as key.

At `#8`, we save the ids in the order by which the orm has given them and save it
to `lcontext.sorted_ids`. This step isn't necessary to all models. In fact, it
is only done in `res.partner` and `product.product` records.

### Extending

In core `point_of_sale`, the loader methods are already defined. However, when creating a new odoo module that will extend `point_of_sale`, we might need to add something in the loaded data. To do so, you can do the following:

```py
class PosSession(models.Model):
    _inherit = "pos.session"

    @loader("hr.employee", ["name", "id", "user_id"])
    def _load_hr_employee(self, lcontext):
        if len(self.config_id.employee_ids) > 0:
            domain = ["&", ("company_id", "=", self.config_id.company_id.id), "|", ("user_id", "=", self.user_id.id), ("id", "in", self.config_id.employee_ids.ids)]
        else:
            domain = [("company_id", "=", self.config_id.company_id.id)]
        records = self.env[lcontext.model].search(domain).read(lcontext.fields, load=False)
        for record in records:
            lcontext.contents[record["id"]] = record
```

The code above is directly taken from `pos_hr`. What the code does is it
registers a `loader` method to load `hr.employee` records and we are only
concerned with `'name'`, `'id'` and `'user_id'` fields.

We can also override the loader method just as we override other model
methods. Look at `_load_product_product` in `pos_cache` for example.

## Extending POS UI

### The Basics: `PointOfSaleUI`

POS UI is a single page application written using the OWL framework. Basically,
the app is composed of tree of `owl.Component`s by which the rendering is
handled by the OWL framework. All we have to do as developers is to declare this
tree of components.

Each component is defined by at least two information:

1. owl QWeb template
2. `owl.Component` subclass

In POS, each component is actually defined by an owl QWeb template and an
`owl.Component` subclass. `style` is actually the 3rd information but POS isn't
using such owl feature. All `style` declaration is done in `pos.css` and in
other css files loaded in the `point_of_sale.index`.

Let's take an example the root component of POS UI which is the `PointOfSaleUI`
component. It is defined like so:

```js
class PointOfSaleUI extends PosComponent {
    ...
}
PointOfSaleUI.components = { ... };
PointOfSaleUI.template = 'point_of_sale.PointOfSaleUI';
```

```xml
<div t-name="point_of_sale.PointOfSaleUI" owl="1">
    <div class="pos">
        ...
    </div>
</div>
```

Note that in the above example, the details are omitted and it just shows the
boilerplate on declaring an `owl.Component` used in POS.

### The Basics: POS UI State Management

POS UI doesn't very much depend on the state management provided by the owl
framework, instead, we develop a custom reactive approach where the view reacts
on every action that is triggered. Simply, the following steps:

1. `view` is rendered based on the `state`.
2. An event is triggered (e.g. button click) which results to dispatch of an `action`.
3. The dispatched `action` mutates the `state`.
4. When `action` is done, go back to 1.

To achieve this designed, we introduced the `PointOfSaleModel` which contains
the `state` data and the `action` methods that mutates the `state`.

For illustration, let's look into the following:

```js
class PointOfSaleModel extends EventBus {
    constructor() {
        super(...arguments);
        this.data = { count: 1 };
    }
    /**
     * @param {number} by
     */
    async actionIncrement(by) {
        this.data.count += by;
    }
}
```

Say we have the `actionIncrement` defined in `PointOfSaleModel`. When this
method is called using the `actionHandler` method of `PointOfSaleModel` like so:
`model.actionHandler({ name: 'actionIncrement', args: [5] })`, the POS UI will
rerender. We can think of `actionHandler` as the dispatcher of the action, such
that when an action is dispatched, the POS UI rerenders which results to the
update in the view.

There is a single instance of `PointOfSaleModel` and it is set as `model` in the
`env` of each `owl.Component`, therefore, you will observe in the source code
the following where a dispatch of an action is bound to an event:

```xml
<div t-name="point_of_sale.SomeTemplate" owl="1">
    <button t-on-click="env.actionHandler({ name: 'actionIncrement', args: [1] })">
        Click me [<t t-esc="env.model.data.count" />]
    </button>
</div>
```

So in the above template, if the button is clicked, the `actionIncrement` will
be dispatched and once the action is done, the view will rerender showing the
modified `count` value in the button.

### Extending the POS UI: Components

We don't explicitly specify the _extension points_ of POS UI, instead, you can
think that every aspect of POS UI is extensible -- from what is displayed in the
view up to how an action behaves. First, let's take a look on to how to make
modification of the view. We do this by extending the POS UI's components. Every
descendant component and element of `PointOfSaleUI` is extensible. For example,
`ProductScreen` is a component in `PointOfSaleUI`, and `SetPricelistButton` is a
component inside `ProductScreen`. Since `SetPricelistButton` is a descendant of
`PointOfSaleUI`, then it can be extended. Of course, `ProductScreen` can also be
extended. We do this by (1) extending in-place the components template and/or by
(2) 'patching' the component class.

#### 1. extend in-place the owl templates

```xml
    <t t-name="pos_extension.ReceiptScreen" t-inherit="point_of_sale.ReceiptScreen" t-inherit-mode="extension" owl="1">
        <xpath expr="//div[hasclass('pos-receipt-container')]" position="inside">
            <NewComponent />
            <AnotherComponent t-if="shouldShowAnotherComponent()" />
        </xpath>
    </t>
```

When extending owl templates in-place, we just perform the typical `xpath`ing we
do in odoo. The attribute `t-inherit-mode="extension"` is important because it
says that qweb should not create a new template, but just do what is declared in
the `xpath` segment on the inherited template. In the above example, we are
adding to the `ReceiptScreen` inside the `pos-receipt-container div` two new
components - the `NewComponent` and `AnotherComponent`.

#### 2. 'patching' the component

When making changes in the template, sometimes a component is rendered
conditionally, just like the `AnotherComponent` in the above example. The
`shouldShowAnotherComponent` method should be available in the `ReceiptScreen`
component. To do this, we use the `patch` method from the `web` module. For more
info about the `patch` method, see its docs in the `web` module.

Let's refer to the following for example.

```js
import ReceiptScreen from 'point_of_sale.ReceiptScreen'; //1
import NewComponent from 'pos_extension.NewComponent'; //2
import AnotherComponent from 'pos_extension.AnotherComponent'; //3
import { patch } from 'web.utils'; //4

//5
patch(ReceiptScreen.prototype, 'pos_restaurant', {
    //6
    shouldShowAnotherComponent() {
        return this.env.model.config.show_another_component;
    },
});

//7
patch(ReceiptScreen, 'pos_restaurant', {
    //8
    components: { ...ReceiptScreen.components },
});

export default ReceiptScreen; //9
```

Remember that in the template, we are rendering two other components inside
`ReceiptScreen`. In order for this to succeed, `ReceiptScreen` should know about
them, therefore, we patch the _static_ properties of the component at `//7` and
`//8`.

`AnotherComponent` is conditionally rendered and is dependent on the instance
method `shouldShowAnotherComponent` therefore, we also define it at `//5` and
`//6`. Note that we patch the component's `prototype` because we are adding an
instance method.

But we have to make sure that `NewComponent` and `AnotherComponent` are properly
declared so we import them at `//2` and `//3`, respectively.

### Extending the POS UI: PointOfSaleModel

The most of the state of the POS UI resides in the `PointOfSaleModel`. (We said
'most' because it is possible that a component can have its own local state
using the `useState` hook.) And this state is mutated using an action. We can
therefore think that `PointOfSaleModel` is a collection of actions and data. You
will also find a lot of getter methods in this class. By convention, if a getter
is used in multiple components, we define the getter in the `PointOfSaleModel`,
otherwise, we define the getter in the component class.

To extend the model, we patch the `PointOfSaleModel` just like we how we patch
component classes:

```js
import PointOfSaleModel from 'point_of_sale.PointOfSaleModel';
import { patch } from 'web.utils';

patch(PointOfSaleModel.prototype, 'pos_hr', {
    async actionAddProduct(order) {
        if (!order.lines.length) {
            order.employee_id = this.data.uiState.activeEmployeeId;
        }
        return this._super(...arguments);
    },
}

export default PointOfSaleModel;
```

In the above example, we are overriding the behavior of `actionAddProduct` such
that when the order has no lines, then we change the employee set to the order
to the current employee.

Note the use of `this._super` to call the super method. We are not using the
native `super` because `web.utils.patch` is not doing a class inheritance.

`PointOfSaleModel` is a huge class because it contains all the actions and a lot
getters. We can also find in the class the methods that post-processes the data
after calling `load_pos_data`. And other methods related to the persistence of
orders to the `localStorage`. It's a big class and it is hoped to be
fully-documented.

## POS Dialogs (aka Popups)

There are predefined dialogs that can be used in the POS UI which includes, but
not limited to, `ConfirmPopup`, `NumberPopup`, and `ErrorPopup`. These dialogs
can be used in `PointOfSaleModel` or in each component.

### Consuming POS dialogs

A `ui` field is reserved in the instance of `PointOfSaleModel` which contains
ui-related methods which include `askUser`. `askUser` is the method that shows
the dialog to the user and waits for the user's response.

```js
// inside a component
this.env.ui.askUser('ConfirmPopup', { title: 'Are you sure?' }).then((response) => {
    if (response) {
        // do something if response is true
    }
});

// in PointOfSaleModel
this.ui.askUser('NumberPopup', { title: 'How old are you?' }).then(([confirm, inputNumberStr]) => {
    if (confirm) {
        // do something on inputNumberStr
    }
});
```

Since call to `askUser` returns a promise, we can conveniently do the following
inside and async method:

```js
async () => {
    const [confirm, inputNumberStr] = await this.ui.askUser('NumberPopup', { title: 'How old are you?' });
    if (confirm) {
        // do something on inputNumberStr
    }
};
```

### POS Dialog Limitation

There is a very limiting limitation of POS Dialogs, that is, we can only show
one dialog at a time. This means we can't render a dialog on top of an existing
dialog. Hopefully future development will remove this limitation.

### Creating a custom POS dialog

A POS dialog is just a normal `owl.Component` (rendered inside the `PosDialog`
component), it is however given a props called `respondWith` by default when
rendered. This method should be called passing the response of the user. If you
look into the implementation of `ConfirmPopup`, when button `okay` is clicked,
`props.respondWith(true)` is called.

Once you have defined the popup component with `props.respondWith` properly
called at some user action, you will have to register the dialog component to
the `PosDialog` component. `PosDialog` is basically the one that controls custom
dialogs. In an extension module, we can do the following to register the custom
dialog we created:

```js
import PosDialog from 'point_of_sale.PosDialog';
import NewCustomPopup from 'pos_extension.NewCustomPopup';
import { patch } from 'web.utils';

patch(PosDialog, 'pos_extension', {
    components: { ...PosDialog.components, NewCustomPopup },
});

export default PosDialog;
```

## `point_of_sale.index` and `point_of_sale.assets`

POS UI assets are loaded in the `point_of_sale.index` template. In fact, when
opening a pos session, it is the template that is rendered by the server to load
the POS UI.

To make sure that all new (and custom) developments are properly loaded, the new
files have to be declared in the `point_of_sale.index`. This template is
actually rendering several assets declaration including `point_of_sale.assets` -
the one that contains the `js` and `css` assets of the POS UI. So to load new
assets, you have to declare the assets in the `__manifest__.py` file like so:

```py
{
    ...
    'assets': {
        'point_of_sale.assets': [
            'pos_extension/static/src/js/**/*.js',
            'pos_extension/static/src/js/**/*.css',
        ],
    }
    ...
}
```
