const dom = new (require("jsdom").JSDOM)(`<!DOCTYPE html><html><body><div id="div"><p id="p1">hello</p><p id="p2">world</p></div></body></html>`);
const doc = dom.window.document;
const p1 = doc.getElementById("p1");
const div = doc.getElementById("div");

const range = doc.createRange();
range.setStart(p1, 0);
range.setEnd(p1, 1);

console.log("p1, 0:", range.isPointInRange(p1, 0));
console.log("p1, 1:", range.isPointInRange(p1, 1));
console.log("div, 1:", range.isPointInRange(div, 1)); // between p1 and p2
console.log("div, 0:", range.isPointInRange(div, 0)); // before p1
