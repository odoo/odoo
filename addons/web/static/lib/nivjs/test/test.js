
module("Class");

test("Class exists", function() {
	ok(!!niv.Class, "Class does not exist");
	ok(!!niv.Class.extend, "extend does not exist");
});

