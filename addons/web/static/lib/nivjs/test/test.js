
module("Class");

test("base", function() {
    ok(!!niv.Class, "Class does not exist");
    ok(!!niv.Class.extend, "extend does not exist");
    var Claz = niv.Class.extend({
        test: function() {
            return "ok";
        }
    })
    equal("ok", new Claz().test());
});

module("DestroyableMixin");

test("base", function() {
    var Claz = niv.Class.extend(_.extend({}, niv.DestroyableMixin, {}));
    var x = new Claz();
    equal(false, !!x.isDestroyed());
    x.destroy();
    equal(true, x.isDestroyed());
});

module("ParentedMixin");

test("base", function() {
    var Claz = niv.Class.extend(_.extend({}, niv.ParentedMixin, {}));
    var x = new Claz();
    var y = new Claz();
    y.setParent(x);
    equal(x, y.getParent());
    equal(y, x.getChildren()[0]);
    x.destroy();
    equal(true, y.isDestroyed());
});

module("Events");

test("base", function() {
    var x = new niv.internal.Events();
    var tmp = 0;
    var fct = function() {tmp = 1;};
    x.on("test", fct);
    equal(0, tmp);
    x.trigger("test");
    equal(1, tmp);
    tmp = 0;
    x.off("test", fct);
    x.trigger("test");
    equal(0, tmp);
});

module("EventDispatcherMixin");

test("base", function() {
    var Claz = niv.Class.extend(_.extend({}, niv.EventDispatcherMixin, {}));
    var x = new Claz();
    var y = new Claz();
    var tmp = 0;
    var fct = function() {tmp = 1;};
    x.bind("test", y, fct);
    equal(0, tmp);
    x.trigger("test");
    equal(1, tmp);
    tmp = 0;
    x.unbind("test", y, fct);
    x.trigger("test");
    equal(0, tmp);
    tmp = 0;
    x.bind("test", y, fct);
    y.destroy();
    x.trigger("test");
    equal(0, tmp);
});
