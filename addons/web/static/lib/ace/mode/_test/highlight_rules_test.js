var fs = require("fs");
var path = require("path");
if (!fs.existsSync)
    fs.existsSync = path.existsSync;

require("amd-loader");

var cwd = __dirname + "/";
var root = path.normalize(cwd + Array(5).join("../"));

function jsFileList(path, filter) {
    if (!filter) filter = /_test/;
    return fs.readdirSync(path).map(function(x) {
        if (x.slice(-3) == ".js" && !filter.test(x) && !/\s/.test(x))
            return x.slice(0, -3);
    }).filter(Boolean);
}

function modeList() {
    return jsFileList(cwd + "../", /_highlight_rules|_test|_worker|xml_util|_outdent|behaviour|completions/);
}

function checkModes() {
    modeList().forEach(function(modeName) {
        try {
            var Mode = require("../" + modeName).Mode;
        } catch(e) {
            console.warn("Can't load mode :" + modeName, e);
            return;
        }
        var m = new Mode();
        if (!("lineCommentStart" in m) && !("blockComment" in m))
            console.warn("missing comment in " + modeName);
        if (!m.$id)
            console.warn("missing id in " + modeName);
        var tokenizer = (new Mode).getTokenizer();
        
        testComments(m.lineCommentStart, testLineComment, tokenizer, modeName);
        testComments(m.blockComment, testBlockComment, tokenizer, modeName);
    });
    
    function testComments(desc, fn, tokenizer, modeName) {
        if (desc) {
            if (Array.isArray(desc)) {
                desc.forEach(function(x) {
                    fn(tokenizer, x, modeName)
                });
            } else {
                fn(tokenizer, desc, modeName)
            }
        }
    }
    
    function testBlockComment(tokenizer, blockComment, modeName) {
        if (blockComment.lineStartOnly)
            return; // TODO test 
        var str = blockComment.start + " " + blockComment.end;
        str = blockComment.start + str;
        if (blockComment.nestable)
            str += blockComment.end;     
        var data = tokenizer.getLineTokens(str, "start");
        var isBroken = data.tokens.some(function(t) { return !/comment/.test(t.type) });
        if (isBroken)
            console.warn("broken blockComment in " + modeName, data);
        if (!/start/.test(data.state))
            console.warn("broken state after blockComment in " + modeName, data);
    }
    
    function testLineComment(tokenizer, commentStart, modeName) {
        var tokens = tokenizer.getLineTokens(commentStart + " ", "start").tokens;
        if (!/comment/.test(tokens[0].type))
            console.warn("broken lineCommentStart in " + modeName);
    }
}

function generateTestData() {
    var docRoot = root + "/demo/kitchen-sink/docs";
    var docs = fs.readdirSync(docRoot);
    var specialDocs = fs.readdirSync(cwd);
    var modes = modeList();

    // console.log("Docs:", docs);
    // console.log("Modes:", modes);

    docs.forEach(function(docName) {
        var p = docName.toLowerCase().split(".");
        if (!p[1])
            return;
        var modeName;
        if (modes.indexOf(p[0]) != -1)
            modeName = p[0];
        else if (modes.indexOf(p[1]) != -1)
            modeName = p[1];
        else
            modeName = {"txt": "text", cpp: "c_cpp"}[p[1]];

        var filePath = "text_" + modeName + ".txt";
        if (specialDocs.indexOf(filePath) == -1) {
            filePath = docRoot + "/" + docName;
        } else {
            filePath = cwd + filePath;
        }

        var text = fs.readFileSync(filePath, "utf8");
        try {
            var Mode = require("../" + modeName).Mode;
        } catch(e) {
            console.warn("Can't load mode :" + modeName, p, e);
            return;
        }
        console.log(modeName);
        var tokenizer = new Mode().getTokenizer();

        var state = "start";
        var data = text.split(/\r\n|\r|\n/).map(function(line) {
            var data = tokenizer.getLineTokens(line, state);
            var tmp = [];
            tmp.push(JSON.stringify(data.state));
            var tokenizedLine = "";
            data.tokens.forEach(function(x) {
                tokenizedLine += x.value;
                tmp.push(JSON.stringify([x.type, x.value]));
            });
            if (tokenizedLine != line)
                tmp.push(JSON.stringify(line));
            state = data.state;
            return tmp.join(",\n  ");
        });
        
        var jsonStr = "[[\n   " + data.join("\n],[\n   ") + "\n]]";
        fs.writeFileSync(cwd + "tokens_" + modeName + ".json", jsonStr, "utf8");
    });
}

function test(startAt) {
    var modes = fs.readdirSync(cwd).map(function(x) {
        return (x.match(/tokens_(.*).json/) || {})[1];
    }).filter(function(x){return !!x});

    for (var i = Math.max(0, startAt||0); i < modes.length; i++)
        testMode(modes[i], i);

    console.log("\u001b[32m" + "all ok" + "\u001b[0m");
}
function testMode(modeName, i) {
    console.log(padNumber(i+1, 3) + ") testing: \u001b[33m" + modeName + "\u001b[0m");

    var text = fs.readFileSync(cwd + "tokens_" + modeName + ".json", "utf8");
    var data = JSON.parse(text);
    var Mode = require("../" + modeName).Mode;
    var tokenizer = new Mode().getTokenizer();

    var state = "start";
    data.forEach(function(lineData) {
        lineData.values = [];
        lineData.types = [];
        lineData.state = lineData.shift();
        var line = null;
        if (typeof lineData[lineData.length - 1] == "string")
            line = lineData.pop();
        lineData.forEach(function(x) {
            lineData.types.push(x[0]);
            lineData.values.push(x[1]);
        });
        if (typeof line != "string")
            line = lineData.values.join("");

        var tokens = tokenizer.getLineTokens(line, state);
        var values = tokens.tokens.map(function(x) {return x.value;});
        var types = tokens.tokens.map(function(x) {return x.type;});

        var err = testEqual([
            JSON.stringify(lineData.state), JSON.stringify(tokens.state),
            lineData.types, types,
            lineData.values, values]);
        
        if (err) {
            console.log(line);
            throw "error";
        }

        state = tokens.state;
    });
}
function testEqual(a) {
    var err;
    if (a[0] + "" !== a[1] + "") {
        console.log(a[0],a[1]);
        err = 1;
    }

    if ( a[2] + "" !== a[3] + "" || a[4] + "" !== a[5] + "") {
        arrayDiff(a[2],a[3]);
        arrayDiff(a[4],a[5]);
        err = 1;
    }
    return err;
}
function arrayDiff(a1, a2) {
    var l = Math.max(a1.length, a2.length);
    var out = [];
    for (var i = 0; i < l; i++) {
        out.push("\n", padNumber(i+1, 3), ") ");
        if (a1[i] !== a2[i])
            out.push("\u001b[31m", a1[i], "\u001b[0m != \u001b[32m", a2[i], "\u001b[0m");
        else
            out.push(a1[i]);
    }
    console.log(out.join(""));
}
function padNumber(num, digits) {
    return ("      " + num).slice(-digits);
}

// cli
var arg = process.argv[2];
if (!arg) {
    test();
    checkModes();
} else if (/--?g(en)?/.test(arg))
    generateTestData(process.argv.splice(3));
else if (/--?c(heck)?/.test(arg))
    checkModes(process.argv.splice(3));
else if (/\d+/.test(arg))
    test(parseInt(process.argv[2],10) || 0);
else
    testMode(arg, -1);