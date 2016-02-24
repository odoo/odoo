"use strict";

var dom     = require('node-jsdom/lib/jsdom/living');
var browser = require('node-jsdom/lib/jsdom/browser/index').browserAugmentation(dom);
var doc = new browser.HTMLDocument({parsingMode: 'html'});
doc.write("<html><head></head><body></body></html>");
browser.document = doc;
browser.window = doc.defaultView;

global.document     = browser.document;
global.window       = browser.window;
global.self         = browser.self;
global.navigator    = browser.navigator;
global.location     = browser.location;
