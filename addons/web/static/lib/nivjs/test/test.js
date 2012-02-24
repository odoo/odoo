
module("Class");

test("base", function() {
    ok(!!niv.Class, "Class does not exist");
    ok(!!niv.Class.extend, "extend does not exist");
    var Claz = niv.Class.extend({
        test: function() {
            return "ok";
        }
    })
    equal(new Claz().test(), "ok");
});

module("DestroyableMixin");

test("base", function() {
    var Claz = niv.Class.extend(_.extend({}, niv.DestroyableMixin, {}));
    var x = new Claz();
    equal(!!x.isDestroyed(), false);
    x.destroy();
    equal(x.isDestroyed(), true);
});

module("ParentedMixin");

test("base", function() {
    var Claz = niv.Class.extend(_.extend({}, niv.ParentedMixin, {}));
    var x = new Claz();
    var y = new Claz();
    y.setParent(x);
    equal(y.getParent(), x);
    equal(x.getChildren()[0], y);
    x.destroy();
    equal(y.isDestroyed(), true);
});

module("Events");

test("base", function() {
    var x = new niv.internal.Events();
    var tmp = 0;
    var fct = function() {tmp = 1;};
    x.on("test", fct);
    equal(tmp, 0);
    x.trigger("test");
    equal(tmp, 1);
    tmp = 0;
    x.off("test", fct);
    x.trigger("test");
    equal(tmp, 0);
});

module("EventDispatcherMixin");

test("base", function() {
    var Claz = niv.Class.extend(_.extend({}, niv.EventDispatcherMixin, {}));
    var x = new Claz();
    var y = new Claz();
    var tmp = 0;
    var fct = function() {tmp = 1;};
    x.bind("test", y, fct);
    equal(tmp, 0);
    x.trigger("test");
    equal(tmp, 1);
    tmp = 0;
    x.unbind("test", y, fct);
    x.trigger("test");
    equal(tmp, 0);
    tmp = 0;
    x.bind("test", y, fct);
    y.destroy();
    x.trigger("test");
    equal(tmp, 0);
});

module("GetterSetterMixin");

test("base", function() {
    var Claz = niv.Class.extend(_.extend({}, niv.GetterSetterMixin, {}));
    var x = new Claz();
    var y = new Claz();
    x.set({test: 1});
    equal(x.get("test"), 1);
    var tmp = 0;
    x.bind("changed:test", y, function(arg) {
        tmp = 1;
        equal(arg.oldValue, 1);
        equal(arg.newValue, 2);
        equal(x.get("test"), 2);
        equal(arg.source, x);
    });
    x.set({test: 2});
    equal(tmp, 1);
});
