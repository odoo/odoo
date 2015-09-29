define(function(require, exports, module) {
module.exports = (function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);throw new Error("Cannot find module '"+o+"'")}var f=n[o]={exports:{}};t[o][0].call(f.exports,function(e){var n=t[o][1][e];return s(n?n:e)},f,f.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({
1:[function(_dereq_,module,exports){
// This file was generated on Thu Jul 24, 2014 15:01 (UTC+01) by REx v5.30 which is Copyright (c) 1979-2014 by Gunther Rademacher <grd@gmx.net>
// REx command line: XQueryTokenizer.ebnf -ll 2 -backtrack -tree -javascript -a xqlint

                                                            // line 2 "XQueryTokenizer.ebnf"
                                                            var XQueryTokenizer = exports.XQueryTokenizer = function XQueryTokenizer(string, parsingEventHandler)
                                                            {
                                                              init(string, parsingEventHandler);
                                                            // line 9 "XQueryTokenizer.js"
  var self = this;

  this.ParseException = function(b, e, s, o, x)
  {
    var
      begin = b,
      end = e,
      state = s,
      offending = o,
      expected = x;

    this.getBegin = function() {return begin;};
    this.getEnd = function() {return end;};
    this.getState = function() {return state;};
    this.getExpected = function() {return expected;};
    this.getOffending = function() {return offending;};

    this.getMessage = function()
    {
      return offending < 0 ? "lexical analysis failed" : "syntax error";
    };
  };

  function init(string, parsingEventHandler)
  {
    eventHandler = parsingEventHandler;
    input = string;
    size = string.length;
    reset(0, 0, 0);
  }

  this.getInput = function()
  {
    return input;
  };

  function reset(l, b, e)
  {
            b0 = b; e0 = b;
    l1 = l; b1 = b; e1 = e;
    end = e;
    eventHandler.reset(input);
  }

  this.getOffendingToken = function(e)
  {
    var o = e.getOffending();
    return o >= 0 ? XQueryTokenizer.TOKEN[o] : null;
  };

  this.getExpectedTokenSet = function(e)
  {
    var expected;
    if (e.getExpected() < 0)
    {
      expected = XQueryTokenizer.getTokenSet(- e.getState());
    }
    else
    {
      expected = [XQueryTokenizer.TOKEN[e.getExpected()]];
    }
    return expected;
  };

  this.getErrorMessage = function(e)
  {
    var tokenSet = this.getExpectedTokenSet(e);
    var found = this.getOffendingToken(e);
    var prefix = input.substring(0, e.getBegin());
    var lines = prefix.split("\n");
    var line = lines.length;
    var column = lines[line - 1].length + 1;
    var size = e.getEnd() - e.getBegin();
    return e.getMessage()
         + (found == null ? "" : ", found " + found)
         + "\nwhile expecting "
         + (tokenSet.length == 1 ? tokenSet[0] : ("[" + tokenSet.join(", ") + "]"))
         + "\n"
         + (size == 0 || found != null ? "" : "after successfully scanning " + size + " characters beginning ")
         + "at line " + line + ", column " + column + ":\n..."
         + input.substring(e.getBegin(), Math.min(input.length, e.getBegin() + 64))
         + "...";
  };

  this.parse_start = function()
  {
    eventHandler.startNonterminal("start", e0);
    lookahead1W(14);                // ModuleDecl | Annotation | OptionDecl | Operator | Variable | Tag | AttrTest |
                                    // Wildcard | EQName^Token | IntegerLiteral | DecimalLiteral | DoubleLiteral |
                                    // S^WS | EOF | '!' | '"' | "'" | '(' | '(#' | '(:' | '(:~' | ')' | ',' | '.' |
                                    // '/' | ':' | ';' | '<!--' | '<![CDATA[' | '<?' | '[' | ']' | 'after' |
                                    // 'allowing' | 'ancestor' | 'ancestor-or-self' | 'and' | 'as' | 'ascending' |
                                    // 'at' | 'attribute' | 'base-uri' | 'before' | 'boundary-space' | 'break' |
                                    // 'case' | 'cast' | 'castable' | 'catch' | 'child' | 'collation' | 'comment' |
                                    // 'constraint' | 'construction' | 'context' | 'continue' | 'copy' |
                                    // 'copy-namespaces' | 'count' | 'decimal-format' | 'declare' | 'default' |
                                    // 'delete' | 'descendant' | 'descendant-or-self' | 'descending' | 'div' |
                                    // 'document' | 'document-node' | 'element' | 'else' | 'empty' | 'empty-sequence' |
                                    // 'encoding' | 'end' | 'eq' | 'every' | 'except' | 'exit' | 'external' | 'first' |
                                    // 'following' | 'following-sibling' | 'for' | 'ft-option' | 'function' | 'ge' |
                                    // 'group' | 'gt' | 'idiv' | 'if' | 'import' | 'in' | 'index' | 'insert' |
                                    // 'instance' | 'integrity' | 'intersect' | 'into' | 'is' | 'item' | 'last' |
                                    // 'lax' | 'le' | 'let' | 'loop' | 'lt' | 'mod' | 'modify' | 'module' |
                                    // 'namespace' | 'namespace-node' | 'ne' | 'node' | 'nodes' | 'only' | 'option' |
                                    // 'or' | 'order' | 'ordered' | 'ordering' | 'parent' | 'preceding' |
                                    // 'preceding-sibling' | 'processing-instruction' | 'rename' | 'replace' |
                                    // 'return' | 'returning' | 'revalidation' | 'satisfies' | 'schema' |
                                    // 'schema-attribute' | 'schema-element' | 'score' | 'self' | 'sliding' | 'some' |
                                    // 'stable' | 'start' | 'strict' | 'switch' | 'text' | 'to' | 'treat' | 'try' |
                                    // 'tumbling' | 'type' | 'typeswitch' | 'union' | 'unordered' | 'updating' |
                                    // 'validate' | 'value' | 'variable' | 'version' | 'where' | 'while' | 'with' |
                                    // 'xquery' | '{' | '|' | '}'
    switch (l1)
    {
    case 55:                        // '<![CDATA['
      shift(55);                    // '<![CDATA['
      break;
    case 54:                        // '<!--'
      shift(54);                    // '<!--'
      break;
    case 56:                        // '<?'
      shift(56);                    // '<?'
      break;
    case 40:                        // '(#'
      shift(40);                    // '(#'
      break;
    case 42:                        // '(:~'
      shift(42);                    // '(:~'
      break;
    case 41:                        // '(:'
      shift(41);                    // '(:'
      break;
    case 35:                        // '"'
      shift(35);                    // '"'
      break;
    case 38:                        // "'"
      shift(38);                    // "'"
      break;
    case 274:                       // '}'
      shift(274);                   // '}'
      break;
    case 271:                       // '{'
      shift(271);                   // '{'
      break;
    case 39:                        // '('
      shift(39);                    // '('
      break;
    case 43:                        // ')'
      shift(43);                    // ')'
      break;
    case 49:                        // '/'
      shift(49);                    // '/'
      break;
    case 62:                        // '['
      shift(62);                    // '['
      break;
    case 63:                        // ']'
      shift(63);                    // ']'
      break;
    case 46:                        // ','
      shift(46);                    // ','
      break;
    case 48:                        // '.'
      shift(48);                    // '.'
      break;
    case 53:                        // ';'
      shift(53);                    // ';'
      break;
    case 51:                        // ':'
      shift(51);                    // ':'
      break;
    case 34:                        // '!'
      shift(34);                    // '!'
      break;
    case 273:                       // '|'
      shift(273);                   // '|'
      break;
    case 2:                         // Annotation
      shift(2);                     // Annotation
      break;
    case 1:                         // ModuleDecl
      shift(1);                     // ModuleDecl
      break;
    case 3:                         // OptionDecl
      shift(3);                     // OptionDecl
      break;
    case 12:                        // AttrTest
      shift(12);                    // AttrTest
      break;
    case 13:                        // Wildcard
      shift(13);                    // Wildcard
      break;
    case 15:                        // IntegerLiteral
      shift(15);                    // IntegerLiteral
      break;
    case 16:                        // DecimalLiteral
      shift(16);                    // DecimalLiteral
      break;
    case 17:                        // DoubleLiteral
      shift(17);                    // DoubleLiteral
      break;
    case 5:                         // Variable
      shift(5);                     // Variable
      break;
    case 6:                         // Tag
      shift(6);                     // Tag
      break;
    case 4:                         // Operator
      shift(4);                     // Operator
      break;
    case 33:                        // EOF
      shift(33);                    // EOF
      break;
    default:
      parse_EQName();
    }
    eventHandler.endNonterminal("start", e0);
  };

  this.parse_StartTag = function()
  {
    eventHandler.startNonterminal("StartTag", e0);
    lookahead1W(8);                 // QName | S^WS | EOF | '"' | "'" | '/>' | '=' | '>'
    switch (l1)
    {
    case 58:                        // '>'
      shift(58);                    // '>'
      break;
    case 50:                        // '/>'
      shift(50);                    // '/>'
      break;
    case 27:                        // QName
      shift(27);                    // QName
      break;
    case 57:                        // '='
      shift(57);                    // '='
      break;
    case 35:                        // '"'
      shift(35);                    // '"'
      break;
    case 38:                        // "'"
      shift(38);                    // "'"
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("StartTag", e0);
  };

  this.parse_TagContent = function()
  {
    eventHandler.startNonterminal("TagContent", e0);
    lookahead1(11);                 // Tag | EndTag | PredefinedEntityRef | ElementContentChar | CharRef | EOF |
                                    // '<!--' | '<![CDATA[' | '{' | '{{' | '}}'
    switch (l1)
    {
    case 23:                        // ElementContentChar
      shift(23);                    // ElementContentChar
      break;
    case 6:                         // Tag
      shift(6);                     // Tag
      break;
    case 7:                         // EndTag
      shift(7);                     // EndTag
      break;
    case 55:                        // '<![CDATA['
      shift(55);                    // '<![CDATA['
      break;
    case 54:                        // '<!--'
      shift(54);                    // '<!--'
      break;
    case 18:                        // PredefinedEntityRef
      shift(18);                    // PredefinedEntityRef
      break;
    case 29:                        // CharRef
      shift(29);                    // CharRef
      break;
    case 272:                       // '{{'
      shift(272);                   // '{{'
      break;
    case 275:                       // '}}'
      shift(275);                   // '}}'
      break;
    case 271:                       // '{'
      shift(271);                   // '{'
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("TagContent", e0);
  };

  this.parse_AposAttr = function()
  {
    eventHandler.startNonterminal("AposAttr", e0);
    lookahead1(10);                 // PredefinedEntityRef | EscapeApos | AposAttrContentChar | CharRef | EOF | "'" |
                                    // '{' | '{{' | '}}'
    switch (l1)
    {
    case 20:                        // EscapeApos
      shift(20);                    // EscapeApos
      break;
    case 25:                        // AposAttrContentChar
      shift(25);                    // AposAttrContentChar
      break;
    case 18:                        // PredefinedEntityRef
      shift(18);                    // PredefinedEntityRef
      break;
    case 29:                        // CharRef
      shift(29);                    // CharRef
      break;
    case 272:                       // '{{'
      shift(272);                   // '{{'
      break;
    case 275:                       // '}}'
      shift(275);                   // '}}'
      break;
    case 271:                       // '{'
      shift(271);                   // '{'
      break;
    case 38:                        // "'"
      shift(38);                    // "'"
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("AposAttr", e0);
  };

  this.parse_QuotAttr = function()
  {
    eventHandler.startNonterminal("QuotAttr", e0);
    lookahead1(9);                  // PredefinedEntityRef | EscapeQuot | QuotAttrContentChar | CharRef | EOF | '"' |
                                    // '{' | '{{' | '}}'
    switch (l1)
    {
    case 19:                        // EscapeQuot
      shift(19);                    // EscapeQuot
      break;
    case 24:                        // QuotAttrContentChar
      shift(24);                    // QuotAttrContentChar
      break;
    case 18:                        // PredefinedEntityRef
      shift(18);                    // PredefinedEntityRef
      break;
    case 29:                        // CharRef
      shift(29);                    // CharRef
      break;
    case 272:                       // '{{'
      shift(272);                   // '{{'
      break;
    case 275:                       // '}}'
      shift(275);                   // '}}'
      break;
    case 271:                       // '{'
      shift(271);                   // '{'
      break;
    case 35:                        // '"'
      shift(35);                    // '"'
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("QuotAttr", e0);
  };

  this.parse_CData = function()
  {
    eventHandler.startNonterminal("CData", e0);
    lookahead1(1);                  // CDataSectionContents | EOF | ']]>'
    switch (l1)
    {
    case 11:                        // CDataSectionContents
      shift(11);                    // CDataSectionContents
      break;
    case 64:                        // ']]>'
      shift(64);                    // ']]>'
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("CData", e0);
  };

  this.parse_XMLComment = function()
  {
    eventHandler.startNonterminal("XMLComment", e0);
    lookahead1(0);                  // DirCommentContents | EOF | '-->'
    switch (l1)
    {
    case 9:                         // DirCommentContents
      shift(9);                     // DirCommentContents
      break;
    case 47:                        // '-->'
      shift(47);                    // '-->'
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("XMLComment", e0);
  };

  this.parse_PI = function()
  {
    eventHandler.startNonterminal("PI", e0);
    lookahead1(3);                  // DirPIContents | EOF | '?' | '?>'
    switch (l1)
    {
    case 10:                        // DirPIContents
      shift(10);                    // DirPIContents
      break;
    case 59:                        // '?'
      shift(59);                    // '?'
      break;
    case 60:                        // '?>'
      shift(60);                    // '?>'
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("PI", e0);
  };

  this.parse_Pragma = function()
  {
    eventHandler.startNonterminal("Pragma", e0);
    lookahead1(2);                  // PragmaContents | EOF | '#' | '#)'
    switch (l1)
    {
    case 8:                         // PragmaContents
      shift(8);                     // PragmaContents
      break;
    case 36:                        // '#'
      shift(36);                    // '#'
      break;
    case 37:                        // '#)'
      shift(37);                    // '#)'
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("Pragma", e0);
  };

  this.parse_Comment = function()
  {
    eventHandler.startNonterminal("Comment", e0);
    lookahead1(4);                  // CommentContents | EOF | '(:' | ':)'
    switch (l1)
    {
    case 52:                        // ':)'
      shift(52);                    // ':)'
      break;
    case 41:                        // '(:'
      shift(41);                    // '(:'
      break;
    case 30:                        // CommentContents
      shift(30);                    // CommentContents
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("Comment", e0);
  };

  this.parse_CommentDoc = function()
  {
    eventHandler.startNonterminal("CommentDoc", e0);
    lookahead1(5);                  // DocTag | DocCommentContents | EOF | '(:' | ':)'
    switch (l1)
    {
    case 31:                        // DocTag
      shift(31);                    // DocTag
      break;
    case 32:                        // DocCommentContents
      shift(32);                    // DocCommentContents
      break;
    case 52:                        // ':)'
      shift(52);                    // ':)'
      break;
    case 41:                        // '(:'
      shift(41);                    // '(:'
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("CommentDoc", e0);
  };

  this.parse_QuotString = function()
  {
    eventHandler.startNonterminal("QuotString", e0);
    lookahead1(6);                  // PredefinedEntityRef | EscapeQuot | QuotChar | CharRef | EOF | '"'
    switch (l1)
    {
    case 18:                        // PredefinedEntityRef
      shift(18);                    // PredefinedEntityRef
      break;
    case 29:                        // CharRef
      shift(29);                    // CharRef
      break;
    case 19:                        // EscapeQuot
      shift(19);                    // EscapeQuot
      break;
    case 21:                        // QuotChar
      shift(21);                    // QuotChar
      break;
    case 35:                        // '"'
      shift(35);                    // '"'
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("QuotString", e0);
  };

  this.parse_AposString = function()
  {
    eventHandler.startNonterminal("AposString", e0);
    lookahead1(7);                  // PredefinedEntityRef | EscapeApos | AposChar | CharRef | EOF | "'"
    switch (l1)
    {
    case 18:                        // PredefinedEntityRef
      shift(18);                    // PredefinedEntityRef
      break;
    case 29:                        // CharRef
      shift(29);                    // CharRef
      break;
    case 20:                        // EscapeApos
      shift(20);                    // EscapeApos
      break;
    case 22:                        // AposChar
      shift(22);                    // AposChar
      break;
    case 38:                        // "'"
      shift(38);                    // "'"
      break;
    default:
      shift(33);                    // EOF
    }
    eventHandler.endNonterminal("AposString", e0);
  };

  this.parse_Prefix = function()
  {
    eventHandler.startNonterminal("Prefix", e0);
    lookahead1W(13);                // NCName^Token | S^WS | 'after' | 'allowing' | 'ancestor' | 'ancestor-or-self' |
                                    // 'and' | 'as' | 'ascending' | 'at' | 'attribute' | 'base-uri' | 'before' |
                                    // 'boundary-space' | 'break' | 'case' | 'cast' | 'castable' | 'catch' | 'child' |
                                    // 'collation' | 'comment' | 'constraint' | 'construction' | 'context' |
                                    // 'continue' | 'copy' | 'copy-namespaces' | 'count' | 'decimal-format' |
                                    // 'declare' | 'default' | 'delete' | 'descendant' | 'descendant-or-self' |
                                    // 'descending' | 'div' | 'document' | 'document-node' | 'element' | 'else' |
                                    // 'empty' | 'empty-sequence' | 'encoding' | 'end' | 'eq' | 'every' | 'except' |
                                    // 'exit' | 'external' | 'first' | 'following' | 'following-sibling' | 'for' |
                                    // 'ft-option' | 'function' | 'ge' | 'group' | 'gt' | 'idiv' | 'if' | 'import' |
                                    // 'in' | 'index' | 'insert' | 'instance' | 'integrity' | 'intersect' | 'into' |
                                    // 'is' | 'item' | 'last' | 'lax' | 'le' | 'let' | 'loop' | 'lt' | 'mod' |
                                    // 'modify' | 'module' | 'namespace' | 'namespace-node' | 'ne' | 'node' | 'nodes' |
                                    // 'only' | 'option' | 'or' | 'order' | 'ordered' | 'ordering' | 'parent' |
                                    // 'preceding' | 'preceding-sibling' | 'processing-instruction' | 'rename' |
                                    // 'replace' | 'return' | 'returning' | 'revalidation' | 'satisfies' | 'schema' |
                                    // 'schema-attribute' | 'schema-element' | 'score' | 'self' | 'sliding' | 'some' |
                                    // 'stable' | 'start' | 'strict' | 'switch' | 'text' | 'to' | 'treat' | 'try' |
                                    // 'tumbling' | 'type' | 'typeswitch' | 'union' | 'unordered' | 'updating' |
                                    // 'validate' | 'value' | 'variable' | 'version' | 'where' | 'while' | 'with' |
                                    // 'xquery'
    whitespace();
    parse_NCName();
    eventHandler.endNonterminal("Prefix", e0);
  };

  this.parse__EQName = function()
  {
    eventHandler.startNonterminal("_EQName", e0);
    lookahead1W(12);                // EQName^Token | S^WS | 'after' | 'allowing' | 'ancestor' | 'ancestor-or-self' |
                                    // 'and' | 'as' | 'ascending' | 'at' | 'attribute' | 'base-uri' | 'before' |
                                    // 'boundary-space' | 'break' | 'case' | 'cast' | 'castable' | 'catch' | 'child' |
                                    // 'collation' | 'comment' | 'constraint' | 'construction' | 'context' |
                                    // 'continue' | 'copy' | 'copy-namespaces' | 'count' | 'decimal-format' |
                                    // 'declare' | 'default' | 'delete' | 'descendant' | 'descendant-or-self' |
                                    // 'descending' | 'div' | 'document' | 'document-node' | 'element' | 'else' |
                                    // 'empty' | 'empty-sequence' | 'encoding' | 'end' | 'eq' | 'every' | 'except' |
                                    // 'exit' | 'external' | 'first' | 'following' | 'following-sibling' | 'for' |
                                    // 'ft-option' | 'function' | 'ge' | 'group' | 'gt' | 'idiv' | 'if' | 'import' |
                                    // 'in' | 'index' | 'insert' | 'instance' | 'integrity' | 'intersect' | 'into' |
                                    // 'is' | 'item' | 'last' | 'lax' | 'le' | 'let' | 'loop' | 'lt' | 'mod' |
                                    // 'modify' | 'module' | 'namespace' | 'namespace-node' | 'ne' | 'node' | 'nodes' |
                                    // 'only' | 'option' | 'or' | 'order' | 'ordered' | 'ordering' | 'parent' |
                                    // 'preceding' | 'preceding-sibling' | 'processing-instruction' | 'rename' |
                                    // 'replace' | 'return' | 'returning' | 'revalidation' | 'satisfies' | 'schema' |
                                    // 'schema-attribute' | 'schema-element' | 'score' | 'self' | 'sliding' | 'some' |
                                    // 'stable' | 'start' | 'strict' | 'switch' | 'text' | 'to' | 'treat' | 'try' |
                                    // 'tumbling' | 'type' | 'typeswitch' | 'union' | 'unordered' | 'updating' |
                                    // 'validate' | 'value' | 'variable' | 'version' | 'where' | 'while' | 'with' |
                                    // 'xquery'
    whitespace();
    parse_EQName();
    eventHandler.endNonterminal("_EQName", e0);
  };

  function parse_EQName()
  {
    eventHandler.startNonterminal("EQName", e0);
    switch (l1)
    {
    case 77:                        // 'attribute'
      shift(77);                    // 'attribute'
      break;
    case 91:                        // 'comment'
      shift(91);                    // 'comment'
      break;
    case 115:                       // 'document-node'
      shift(115);                   // 'document-node'
      break;
    case 116:                       // 'element'
      shift(116);                   // 'element'
      break;
    case 119:                       // 'empty-sequence'
      shift(119);                   // 'empty-sequence'
      break;
    case 140:                       // 'function'
      shift(140);                   // 'function'
      break;
    case 147:                       // 'if'
      shift(147);                   // 'if'
      break;
    case 160:                       // 'item'
      shift(160);                   // 'item'
      break;
    case 180:                       // 'namespace-node'
      shift(180);                   // 'namespace-node'
      break;
    case 186:                       // 'node'
      shift(186);                   // 'node'
      break;
    case 211:                       // 'processing-instruction'
      shift(211);                   // 'processing-instruction'
      break;
    case 221:                       // 'schema-attribute'
      shift(221);                   // 'schema-attribute'
      break;
    case 222:                       // 'schema-element'
      shift(222);                   // 'schema-element'
      break;
    case 238:                       // 'switch'
      shift(238);                   // 'switch'
      break;
    case 239:                       // 'text'
      shift(239);                   // 'text'
      break;
    case 248:                       // 'typeswitch'
      shift(248);                   // 'typeswitch'
      break;
    default:
      parse_FunctionName();
    }
    eventHandler.endNonterminal("EQName", e0);
  }

  function parse_FunctionName()
  {
    eventHandler.startNonterminal("FunctionName", e0);
    switch (l1)
    {
    case 14:                        // EQName^Token
      shift(14);                    // EQName^Token
      break;
    case 65:                        // 'after'
      shift(65);                    // 'after'
      break;
    case 68:                        // 'ancestor'
      shift(68);                    // 'ancestor'
      break;
    case 69:                        // 'ancestor-or-self'
      shift(69);                    // 'ancestor-or-self'
      break;
    case 70:                        // 'and'
      shift(70);                    // 'and'
      break;
    case 74:                        // 'as'
      shift(74);                    // 'as'
      break;
    case 75:                        // 'ascending'
      shift(75);                    // 'ascending'
      break;
    case 79:                        // 'before'
      shift(79);                    // 'before'
      break;
    case 83:                        // 'case'
      shift(83);                    // 'case'
      break;
    case 84:                        // 'cast'
      shift(84);                    // 'cast'
      break;
    case 85:                        // 'castable'
      shift(85);                    // 'castable'
      break;
    case 88:                        // 'child'
      shift(88);                    // 'child'
      break;
    case 89:                        // 'collation'
      shift(89);                    // 'collation'
      break;
    case 98:                        // 'copy'
      shift(98);                    // 'copy'
      break;
    case 100:                       // 'count'
      shift(100);                   // 'count'
      break;
    case 103:                       // 'declare'
      shift(103);                   // 'declare'
      break;
    case 104:                       // 'default'
      shift(104);                   // 'default'
      break;
    case 105:                       // 'delete'
      shift(105);                   // 'delete'
      break;
    case 106:                       // 'descendant'
      shift(106);                   // 'descendant'
      break;
    case 107:                       // 'descendant-or-self'
      shift(107);                   // 'descendant-or-self'
      break;
    case 108:                       // 'descending'
      shift(108);                   // 'descending'
      break;
    case 113:                       // 'div'
      shift(113);                   // 'div'
      break;
    case 114:                       // 'document'
      shift(114);                   // 'document'
      break;
    case 117:                       // 'else'
      shift(117);                   // 'else'
      break;
    case 118:                       // 'empty'
      shift(118);                   // 'empty'
      break;
    case 121:                       // 'end'
      shift(121);                   // 'end'
      break;
    case 123:                       // 'eq'
      shift(123);                   // 'eq'
      break;
    case 124:                       // 'every'
      shift(124);                   // 'every'
      break;
    case 126:                       // 'except'
      shift(126);                   // 'except'
      break;
    case 129:                       // 'first'
      shift(129);                   // 'first'
      break;
    case 130:                       // 'following'
      shift(130);                   // 'following'
      break;
    case 131:                       // 'following-sibling'
      shift(131);                   // 'following-sibling'
      break;
    case 132:                       // 'for'
      shift(132);                   // 'for'
      break;
    case 141:                       // 'ge'
      shift(141);                   // 'ge'
      break;
    case 143:                       // 'group'
      shift(143);                   // 'group'
      break;
    case 145:                       // 'gt'
      shift(145);                   // 'gt'
      break;
    case 146:                       // 'idiv'
      shift(146);                   // 'idiv'
      break;
    case 148:                       // 'import'
      shift(148);                   // 'import'
      break;
    case 154:                       // 'insert'
      shift(154);                   // 'insert'
      break;
    case 155:                       // 'instance'
      shift(155);                   // 'instance'
      break;
    case 157:                       // 'intersect'
      shift(157);                   // 'intersect'
      break;
    case 158:                       // 'into'
      shift(158);                   // 'into'
      break;
    case 159:                       // 'is'
      shift(159);                   // 'is'
      break;
    case 165:                       // 'last'
      shift(165);                   // 'last'
      break;
    case 167:                       // 'le'
      shift(167);                   // 'le'
      break;
    case 169:                       // 'let'
      shift(169);                   // 'let'
      break;
    case 173:                       // 'lt'
      shift(173);                   // 'lt'
      break;
    case 175:                       // 'mod'
      shift(175);                   // 'mod'
      break;
    case 176:                       // 'modify'
      shift(176);                   // 'modify'
      break;
    case 177:                       // 'module'
      shift(177);                   // 'module'
      break;
    case 179:                       // 'namespace'
      shift(179);                   // 'namespace'
      break;
    case 181:                       // 'ne'
      shift(181);                   // 'ne'
      break;
    case 193:                       // 'only'
      shift(193);                   // 'only'
      break;
    case 195:                       // 'or'
      shift(195);                   // 'or'
      break;
    case 196:                       // 'order'
      shift(196);                   // 'order'
      break;
    case 197:                       // 'ordered'
      shift(197);                   // 'ordered'
      break;
    case 201:                       // 'parent'
      shift(201);                   // 'parent'
      break;
    case 207:                       // 'preceding'
      shift(207);                   // 'preceding'
      break;
    case 208:                       // 'preceding-sibling'
      shift(208);                   // 'preceding-sibling'
      break;
    case 213:                       // 'rename'
      shift(213);                   // 'rename'
      break;
    case 214:                       // 'replace'
      shift(214);                   // 'replace'
      break;
    case 215:                       // 'return'
      shift(215);                   // 'return'
      break;
    case 219:                       // 'satisfies'
      shift(219);                   // 'satisfies'
      break;
    case 224:                       // 'self'
      shift(224);                   // 'self'
      break;
    case 230:                       // 'some'
      shift(230);                   // 'some'
      break;
    case 231:                       // 'stable'
      shift(231);                   // 'stable'
      break;
    case 232:                       // 'start'
      shift(232);                   // 'start'
      break;
    case 243:                       // 'to'
      shift(243);                   // 'to'
      break;
    case 244:                       // 'treat'
      shift(244);                   // 'treat'
      break;
    case 245:                       // 'try'
      shift(245);                   // 'try'
      break;
    case 249:                       // 'union'
      shift(249);                   // 'union'
      break;
    case 251:                       // 'unordered'
      shift(251);                   // 'unordered'
      break;
    case 255:                       // 'validate'
      shift(255);                   // 'validate'
      break;
    case 261:                       // 'where'
      shift(261);                   // 'where'
      break;
    case 265:                       // 'with'
      shift(265);                   // 'with'
      break;
    case 269:                       // 'xquery'
      shift(269);                   // 'xquery'
      break;
    case 67:                        // 'allowing'
      shift(67);                    // 'allowing'
      break;
    case 76:                        // 'at'
      shift(76);                    // 'at'
      break;
    case 78:                        // 'base-uri'
      shift(78);                    // 'base-uri'
      break;
    case 80:                        // 'boundary-space'
      shift(80);                    // 'boundary-space'
      break;
    case 81:                        // 'break'
      shift(81);                    // 'break'
      break;
    case 86:                        // 'catch'
      shift(86);                    // 'catch'
      break;
    case 93:                        // 'construction'
      shift(93);                    // 'construction'
      break;
    case 96:                        // 'context'
      shift(96);                    // 'context'
      break;
    case 97:                        // 'continue'
      shift(97);                    // 'continue'
      break;
    case 99:                        // 'copy-namespaces'
      shift(99);                    // 'copy-namespaces'
      break;
    case 101:                       // 'decimal-format'
      shift(101);                   // 'decimal-format'
      break;
    case 120:                       // 'encoding'
      shift(120);                   // 'encoding'
      break;
    case 127:                       // 'exit'
      shift(127);                   // 'exit'
      break;
    case 128:                       // 'external'
      shift(128);                   // 'external'
      break;
    case 136:                       // 'ft-option'
      shift(136);                   // 'ft-option'
      break;
    case 149:                       // 'in'
      shift(149);                   // 'in'
      break;
    case 150:                       // 'index'
      shift(150);                   // 'index'
      break;
    case 156:                       // 'integrity'
      shift(156);                   // 'integrity'
      break;
    case 166:                       // 'lax'
      shift(166);                   // 'lax'
      break;
    case 187:                       // 'nodes'
      shift(187);                   // 'nodes'
      break;
    case 194:                       // 'option'
      shift(194);                   // 'option'
      break;
    case 198:                       // 'ordering'
      shift(198);                   // 'ordering'
      break;
    case 217:                       // 'revalidation'
      shift(217);                   // 'revalidation'
      break;
    case 220:                       // 'schema'
      shift(220);                   // 'schema'
      break;
    case 223:                       // 'score'
      shift(223);                   // 'score'
      break;
    case 229:                       // 'sliding'
      shift(229);                   // 'sliding'
      break;
    case 235:                       // 'strict'
      shift(235);                   // 'strict'
      break;
    case 246:                       // 'tumbling'
      shift(246);                   // 'tumbling'
      break;
    case 247:                       // 'type'
      shift(247);                   // 'type'
      break;
    case 252:                       // 'updating'
      shift(252);                   // 'updating'
      break;
    case 256:                       // 'value'
      shift(256);                   // 'value'
      break;
    case 257:                       // 'variable'
      shift(257);                   // 'variable'
      break;
    case 258:                       // 'version'
      shift(258);                   // 'version'
      break;
    case 262:                       // 'while'
      shift(262);                   // 'while'
      break;
    case 92:                        // 'constraint'
      shift(92);                    // 'constraint'
      break;
    case 171:                       // 'loop'
      shift(171);                   // 'loop'
      break;
    default:
      shift(216);                   // 'returning'
    }
    eventHandler.endNonterminal("FunctionName", e0);
  }

  function parse_NCName()
  {
    eventHandler.startNonterminal("NCName", e0);
    switch (l1)
    {
    case 26:                        // NCName^Token
      shift(26);                    // NCName^Token
      break;
    case 65:                        // 'after'
      shift(65);                    // 'after'
      break;
    case 70:                        // 'and'
      shift(70);                    // 'and'
      break;
    case 74:                        // 'as'
      shift(74);                    // 'as'
      break;
    case 75:                        // 'ascending'
      shift(75);                    // 'ascending'
      break;
    case 79:                        // 'before'
      shift(79);                    // 'before'
      break;
    case 83:                        // 'case'
      shift(83);                    // 'case'
      break;
    case 84:                        // 'cast'
      shift(84);                    // 'cast'
      break;
    case 85:                        // 'castable'
      shift(85);                    // 'castable'
      break;
    case 89:                        // 'collation'
      shift(89);                    // 'collation'
      break;
    case 100:                       // 'count'
      shift(100);                   // 'count'
      break;
    case 104:                       // 'default'
      shift(104);                   // 'default'
      break;
    case 108:                       // 'descending'
      shift(108);                   // 'descending'
      break;
    case 113:                       // 'div'
      shift(113);                   // 'div'
      break;
    case 117:                       // 'else'
      shift(117);                   // 'else'
      break;
    case 118:                       // 'empty'
      shift(118);                   // 'empty'
      break;
    case 121:                       // 'end'
      shift(121);                   // 'end'
      break;
    case 123:                       // 'eq'
      shift(123);                   // 'eq'
      break;
    case 126:                       // 'except'
      shift(126);                   // 'except'
      break;
    case 132:                       // 'for'
      shift(132);                   // 'for'
      break;
    case 141:                       // 'ge'
      shift(141);                   // 'ge'
      break;
    case 143:                       // 'group'
      shift(143);                   // 'group'
      break;
    case 145:                       // 'gt'
      shift(145);                   // 'gt'
      break;
    case 146:                       // 'idiv'
      shift(146);                   // 'idiv'
      break;
    case 155:                       // 'instance'
      shift(155);                   // 'instance'
      break;
    case 157:                       // 'intersect'
      shift(157);                   // 'intersect'
      break;
    case 158:                       // 'into'
      shift(158);                   // 'into'
      break;
    case 159:                       // 'is'
      shift(159);                   // 'is'
      break;
    case 167:                       // 'le'
      shift(167);                   // 'le'
      break;
    case 169:                       // 'let'
      shift(169);                   // 'let'
      break;
    case 173:                       // 'lt'
      shift(173);                   // 'lt'
      break;
    case 175:                       // 'mod'
      shift(175);                   // 'mod'
      break;
    case 176:                       // 'modify'
      shift(176);                   // 'modify'
      break;
    case 181:                       // 'ne'
      shift(181);                   // 'ne'
      break;
    case 193:                       // 'only'
      shift(193);                   // 'only'
      break;
    case 195:                       // 'or'
      shift(195);                   // 'or'
      break;
    case 196:                       // 'order'
      shift(196);                   // 'order'
      break;
    case 215:                       // 'return'
      shift(215);                   // 'return'
      break;
    case 219:                       // 'satisfies'
      shift(219);                   // 'satisfies'
      break;
    case 231:                       // 'stable'
      shift(231);                   // 'stable'
      break;
    case 232:                       // 'start'
      shift(232);                   // 'start'
      break;
    case 243:                       // 'to'
      shift(243);                   // 'to'
      break;
    case 244:                       // 'treat'
      shift(244);                   // 'treat'
      break;
    case 249:                       // 'union'
      shift(249);                   // 'union'
      break;
    case 261:                       // 'where'
      shift(261);                   // 'where'
      break;
    case 265:                       // 'with'
      shift(265);                   // 'with'
      break;
    case 68:                        // 'ancestor'
      shift(68);                    // 'ancestor'
      break;
    case 69:                        // 'ancestor-or-self'
      shift(69);                    // 'ancestor-or-self'
      break;
    case 77:                        // 'attribute'
      shift(77);                    // 'attribute'
      break;
    case 88:                        // 'child'
      shift(88);                    // 'child'
      break;
    case 91:                        // 'comment'
      shift(91);                    // 'comment'
      break;
    case 98:                        // 'copy'
      shift(98);                    // 'copy'
      break;
    case 103:                       // 'declare'
      shift(103);                   // 'declare'
      break;
    case 105:                       // 'delete'
      shift(105);                   // 'delete'
      break;
    case 106:                       // 'descendant'
      shift(106);                   // 'descendant'
      break;
    case 107:                       // 'descendant-or-self'
      shift(107);                   // 'descendant-or-self'
      break;
    case 114:                       // 'document'
      shift(114);                   // 'document'
      break;
    case 115:                       // 'document-node'
      shift(115);                   // 'document-node'
      break;
    case 116:                       // 'element'
      shift(116);                   // 'element'
      break;
    case 119:                       // 'empty-sequence'
      shift(119);                   // 'empty-sequence'
      break;
    case 124:                       // 'every'
      shift(124);                   // 'every'
      break;
    case 129:                       // 'first'
      shift(129);                   // 'first'
      break;
    case 130:                       // 'following'
      shift(130);                   // 'following'
      break;
    case 131:                       // 'following-sibling'
      shift(131);                   // 'following-sibling'
      break;
    case 140:                       // 'function'
      shift(140);                   // 'function'
      break;
    case 147:                       // 'if'
      shift(147);                   // 'if'
      break;
    case 148:                       // 'import'
      shift(148);                   // 'import'
      break;
    case 154:                       // 'insert'
      shift(154);                   // 'insert'
      break;
    case 160:                       // 'item'
      shift(160);                   // 'item'
      break;
    case 165:                       // 'last'
      shift(165);                   // 'last'
      break;
    case 177:                       // 'module'
      shift(177);                   // 'module'
      break;
    case 179:                       // 'namespace'
      shift(179);                   // 'namespace'
      break;
    case 180:                       // 'namespace-node'
      shift(180);                   // 'namespace-node'
      break;
    case 186:                       // 'node'
      shift(186);                   // 'node'
      break;
    case 197:                       // 'ordered'
      shift(197);                   // 'ordered'
      break;
    case 201:                       // 'parent'
      shift(201);                   // 'parent'
      break;
    case 207:                       // 'preceding'
      shift(207);                   // 'preceding'
      break;
    case 208:                       // 'preceding-sibling'
      shift(208);                   // 'preceding-sibling'
      break;
    case 211:                       // 'processing-instruction'
      shift(211);                   // 'processing-instruction'
      break;
    case 213:                       // 'rename'
      shift(213);                   // 'rename'
      break;
    case 214:                       // 'replace'
      shift(214);                   // 'replace'
      break;
    case 221:                       // 'schema-attribute'
      shift(221);                   // 'schema-attribute'
      break;
    case 222:                       // 'schema-element'
      shift(222);                   // 'schema-element'
      break;
    case 224:                       // 'self'
      shift(224);                   // 'self'
      break;
    case 230:                       // 'some'
      shift(230);                   // 'some'
      break;
    case 238:                       // 'switch'
      shift(238);                   // 'switch'
      break;
    case 239:                       // 'text'
      shift(239);                   // 'text'
      break;
    case 245:                       // 'try'
      shift(245);                   // 'try'
      break;
    case 248:                       // 'typeswitch'
      shift(248);                   // 'typeswitch'
      break;
    case 251:                       // 'unordered'
      shift(251);                   // 'unordered'
      break;
    case 255:                       // 'validate'
      shift(255);                   // 'validate'
      break;
    case 257:                       // 'variable'
      shift(257);                   // 'variable'
      break;
    case 269:                       // 'xquery'
      shift(269);                   // 'xquery'
      break;
    case 67:                        // 'allowing'
      shift(67);                    // 'allowing'
      break;
    case 76:                        // 'at'
      shift(76);                    // 'at'
      break;
    case 78:                        // 'base-uri'
      shift(78);                    // 'base-uri'
      break;
    case 80:                        // 'boundary-space'
      shift(80);                    // 'boundary-space'
      break;
    case 81:                        // 'break'
      shift(81);                    // 'break'
      break;
    case 86:                        // 'catch'
      shift(86);                    // 'catch'
      break;
    case 93:                        // 'construction'
      shift(93);                    // 'construction'
      break;
    case 96:                        // 'context'
      shift(96);                    // 'context'
      break;
    case 97:                        // 'continue'
      shift(97);                    // 'continue'
      break;
    case 99:                        // 'copy-namespaces'
      shift(99);                    // 'copy-namespaces'
      break;
    case 101:                       // 'decimal-format'
      shift(101);                   // 'decimal-format'
      break;
    case 120:                       // 'encoding'
      shift(120);                   // 'encoding'
      break;
    case 127:                       // 'exit'
      shift(127);                   // 'exit'
      break;
    case 128:                       // 'external'
      shift(128);                   // 'external'
      break;
    case 136:                       // 'ft-option'
      shift(136);                   // 'ft-option'
      break;
    case 149:                       // 'in'
      shift(149);                   // 'in'
      break;
    case 150:                       // 'index'
      shift(150);                   // 'index'
      break;
    case 156:                       // 'integrity'
      shift(156);                   // 'integrity'
      break;
    case 166:                       // 'lax'
      shift(166);                   // 'lax'
      break;
    case 187:                       // 'nodes'
      shift(187);                   // 'nodes'
      break;
    case 194:                       // 'option'
      shift(194);                   // 'option'
      break;
    case 198:                       // 'ordering'
      shift(198);                   // 'ordering'
      break;
    case 217:                       // 'revalidation'
      shift(217);                   // 'revalidation'
      break;
    case 220:                       // 'schema'
      shift(220);                   // 'schema'
      break;
    case 223:                       // 'score'
      shift(223);                   // 'score'
      break;
    case 229:                       // 'sliding'
      shift(229);                   // 'sliding'
      break;
    case 235:                       // 'strict'
      shift(235);                   // 'strict'
      break;
    case 246:                       // 'tumbling'
      shift(246);                   // 'tumbling'
      break;
    case 247:                       // 'type'
      shift(247);                   // 'type'
      break;
    case 252:                       // 'updating'
      shift(252);                   // 'updating'
      break;
    case 256:                       // 'value'
      shift(256);                   // 'value'
      break;
    case 258:                       // 'version'
      shift(258);                   // 'version'
      break;
    case 262:                       // 'while'
      shift(262);                   // 'while'
      break;
    case 92:                        // 'constraint'
      shift(92);                    // 'constraint'
      break;
    case 171:                       // 'loop'
      shift(171);                   // 'loop'
      break;
    default:
      shift(216);                   // 'returning'
    }
    eventHandler.endNonterminal("NCName", e0);
  }

  function shift(t)
  {
    if (l1 == t)
    {
      whitespace();
      eventHandler.terminal(XQueryTokenizer.TOKEN[l1], b1, e1 > size ? size : e1);
      b0 = b1; e0 = e1; l1 = 0;
    }
    else
    {
      error(b1, e1, 0, l1, t);
    }
  }

  function whitespace()
  {
    if (e0 != b1)
    {
      b0 = e0;
      e0 = b1;
      eventHandler.whitespace(b0, e0);
    }
  }

  function matchW(set)
  {
    var code;
    for (;;)
    {
      code = match(set);
      if (code != 28)               // S^WS
      {
        break;
      }
    }
    return code;
  }

  function lookahead1W(set)
  {
    if (l1 == 0)
    {
      l1 = matchW(set);
      b1 = begin;
      e1 = end;
    }
  }

  function lookahead1(set)
  {
    if (l1 == 0)
    {
      l1 = match(set);
      b1 = begin;
      e1 = end;
    }
  }

  function error(b, e, s, l, t)
  {
    throw new self.ParseException(b, e, s, l, t);
  }

  var lk, b0, e0;
  var l1, b1, e1;
  var eventHandler;

  var input;
  var size;
  var begin;
  var end;

  function match(tokenSetId)
  {
    var nonbmp = false;
    begin = end;
    var current = end;
    var result = XQueryTokenizer.INITIAL[tokenSetId];
    var state = 0;

    for (var code = result & 4095; code != 0; )
    {
      var charclass;
      var c0 = current < size ? input.charCodeAt(current) : 0;
      ++current;
      if (c0 < 0x80)
      {
        charclass = XQueryTokenizer.MAP0[c0];
      }
      else if (c0 < 0xd800)
      {
        var c1 = c0 >> 4;
        charclass = XQueryTokenizer.MAP1[(c0 & 15) + XQueryTokenizer.MAP1[(c1 & 31) + XQueryTokenizer.MAP1[c1 >> 5]]];
      }
      else
      {
        if (c0 < 0xdc00)
        {
          var c1 = current < size ? input.charCodeAt(current) : 0;
          if (c1 >= 0xdc00 && c1 < 0xe000)
          {
            ++current;
            c0 = ((c0 & 0x3ff) << 10) + (c1 & 0x3ff) + 0x10000;
            nonbmp = true;
          }
        }
        var lo = 0, hi = 5;
        for (var m = 3; ; m = (hi + lo) >> 1)
        {
          if (XQueryTokenizer.MAP2[m] > c0) hi = m - 1;
          else if (XQueryTokenizer.MAP2[6 + m] < c0) lo = m + 1;
          else {charclass = XQueryTokenizer.MAP2[12 + m]; break;}
          if (lo > hi) {charclass = 0; break;}
        }
      }

      state = code;
      var i0 = (charclass << 12) + code - 1;
      code = XQueryTokenizer.TRANSITION[(i0 & 15) + XQueryTokenizer.TRANSITION[i0 >> 4]];

      if (code > 4095)
      {
        result = code;
        code &= 4095;
        end = current;
      }
    }

    result >>= 12;
    if (result == 0)
    {
      end = current - 1;
      var c1 = end < size ? input.charCodeAt(end) : 0;
      if (c1 >= 0xdc00 && c1 < 0xe000) --end;
      return error(begin, end, state, -1, -1);
    }

    if (nonbmp)
    {
      for (var i = result >> 9; i > 0; --i)
      {
        --end;
        var c1 = end < size ? input.charCodeAt(end) : 0;
        if (c1 >= 0xdc00 && c1 < 0xe000) --end;
      }
    }
    else
    {
      end -= result >> 9;
    }

    return (result & 511) - 1;
  }
}

XQueryTokenizer.getTokenSet = function(tokenSetId)
{
  var set = [];
  var s = tokenSetId < 0 ? - tokenSetId : INITIAL[tokenSetId] & 4095;
  for (var i = 0; i < 276; i += 32)
  {
    var j = i;
    var i0 = (i >> 5) * 2062 + s - 1;
    var i1 = i0 >> 2;
    var i2 = i1 >> 2;
    var f = XQueryTokenizer.EXPECTED[(i0 & 3) + XQueryTokenizer.EXPECTED[(i1 & 3) + XQueryTokenizer.EXPECTED[(i2 & 3) + XQueryTokenizer.EXPECTED[i2 >> 2]]]];
    for ( ; f != 0; f >>>= 1, ++j)
    {
      if ((f & 1) != 0)
      {
        set.push(XQueryTokenizer.TOKEN[j]);
      }
    }
  }
  return set;
};

XQueryTokenizer.MAP0 =
[
  /*   0 */ 66, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 3, 4, 5,
  /*  36 */ 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 18, 18, 18, 18, 18, 18, 18, 18, 18, 19, 20, 21, 22, 23, 24,
  /*  64 */ 25, 26, 27, 28, 29, 30, 27, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 32, 31, 31, 33, 31, 31, 31, 31, 31, 31,
  /*  91 */ 34, 35, 36, 35, 31, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 31, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56,
  /* 118 */ 57, 58, 59, 60, 31, 61, 62, 63, 64, 35
];

XQueryTokenizer.MAP1 =
[
  /*   0 */ 108, 124, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 156, 181, 181, 181, 181,
  /*  21 */ 181, 214, 215, 213, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214,
  /*  42 */ 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214,
  /*  63 */ 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214,
  /*  84 */ 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214,
  /* 105 */ 214, 214, 214, 247, 261, 277, 293, 309, 347, 363, 379, 416, 416, 416, 408, 331, 323, 331, 323, 331, 331,
  /* 126 */ 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 433, 433, 433, 433, 433, 433, 433,
  /* 147 */ 316, 331, 331, 331, 331, 331, 331, 331, 331, 394, 416, 416, 417, 415, 416, 416, 331, 331, 331, 331, 331,
  /* 168 */ 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 416, 416, 416, 416, 416, 416, 416, 416,
  /* 189 */ 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416, 416,
  /* 210 */ 416, 416, 416, 330, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331,
  /* 231 */ 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 416, 66, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 256 */ 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
  /* 290 */ 15, 16, 17, 18, 18, 18, 18, 18, 18, 18, 18, 18, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 27, 31,
  /* 317 */ 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 35, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31,
  /* 344 */ 31, 31, 31, 31, 32, 31, 31, 33, 31, 31, 31, 31, 31, 31, 34, 35, 36, 35, 31, 35, 37, 38, 39, 40, 41, 42, 43,
  /* 371 */ 44, 45, 31, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 31, 61, 62, 63, 64, 35, 35, 35, 35,
  /* 398 */ 35, 35, 35, 35, 35, 35, 35, 35, 31, 31, 35, 35, 35, 35, 35, 35, 35, 65, 35, 35, 35, 35, 35, 35, 35, 35, 35,
  /* 425 */ 35, 35, 35, 35, 35, 35, 35, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65
];

XQueryTokenizer.MAP2 =
[
  /*  0 */ 57344, 63744, 64976, 65008, 65536, 983040, 63743, 64975, 65007, 65533, 983039, 1114111, 35, 31, 35, 31, 31,
  /* 17 */ 35
];

XQueryTokenizer.INITIAL =
[
  /*  0 */ 1, 2, 36867, 45060, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
];

XQueryTokenizer.TRANSITION =
[
  /*     0 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*    15 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*    30 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*    45 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*    60 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*    75 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*    90 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   105 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   120 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   135 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   150 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   165 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   180 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   195 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   210 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   225 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   240 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   255 */ 17590, 22908, 18836, 17152, 19008, 19233, 20367, 19008, 17173, 30763, 36437, 17330, 17349, 18921, 17189,
  /*   270 */ 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 17365, 21880, 18649, 18665, 19006, 17265, 22033,
  /*   285 */ 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 17470, 17497, 17520, 17251,
  /*   300 */ 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418, 18157, 21940,
  /*   315 */ 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531,
  /*   330 */ 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 17848, 17880, 18731, 17918, 36551,
  /*   345 */ 17292, 17934, 17979, 18727, 18023, 36545, 18621, 18039, 18056, 18072, 18117, 18143, 18173, 18052, 18209,
  /*   360 */ 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816,
  /*   375 */ 32961, 17687, 18805, 18421, 18437, 18101, 17393, 18489, 18505, 18535, 17590, 17590, 17590, 17590, 17590,
  /*   390 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   405 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   420 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   435 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   450 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   465 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   480 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   495 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   510 */ 17590, 17590, 18579, 21711, 17152, 19008, 19233, 20367, 19008, 28684, 30763, 36437, 17330, 17349, 18921,
  /*   525 */ 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 17365, 21880, 18649, 18665, 19006, 17265,
  /*   540 */ 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 17470, 17497, 17520,
  /*   555 */ 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418, 18157,
  /*   570 */ 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223,
  /*   585 */ 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 17848, 17880, 18731, 17918,
  /*   600 */ 36551, 17292, 17934, 17979, 18727, 18023, 36545, 18621, 18039, 18056, 18072, 18117, 18143, 18173, 18052,
  /*   615 */ 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392,
  /*   630 */ 17816, 32961, 17687, 18805, 18421, 18437, 18101, 17393, 18489, 18505, 18535, 17590, 17590, 17590, 17590,
  /*   645 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   660 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   675 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   690 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   705 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   720 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   735 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   750 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   765 */ 17590, 17590, 17590, 20116, 18836, 18637, 19008, 19233, 21267, 19008, 17173, 30763, 36437, 17330, 17349,
  /*   780 */ 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665, 19006,
  /*   795 */ 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 32952, 17497,
  /*   810 */ 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418,
  /*   825 */ 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473,
  /*   840 */ 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864, 18731,
  /*   855 */ 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143, 18706,
  /*   870 */ 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642,
  /*   885 */ 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590, 17590,
  /*   900 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   915 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   930 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   945 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   960 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   975 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*   990 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1005 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1020 */ 17590, 17590, 17590, 17590, 18763, 18778, 18794, 19008, 19233, 20367, 19008, 17173, 30763, 36437, 17330,
  /*  1035 */ 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665,
  /*  1050 */ 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 32952,
  /*  1065 */ 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258,
  /*  1080 */ 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617,
  /*  1095 */ 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864,
  /*  1110 */ 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143,
  /*  1125 */ 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163,
  /*  1140 */ 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590,
  /*  1155 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1170 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1185 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1200 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1215 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1230 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1245 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1260 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1275 */ 17590, 17590, 17590, 17590, 17590, 18821, 22923, 18906, 19008, 19233, 17431, 19008, 17173, 30763, 36437,
  /*  1290 */ 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18937, 21880, 18649,
  /*  1305 */ 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 19054, 17311, 18658, 18999, 19008, 17447,
  /*  1320 */ 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 18953, 21887, 17504, 17527,
  /*  1335 */ 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946,
  /*  1350 */ 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156,
  /*  1365 */ 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117,
  /*  1380 */ 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796,
  /*  1395 */ 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590,
  /*  1410 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1425 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1440 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1455 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1470 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1485 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1500 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1515 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1530 */ 17590, 17590, 17590, 17590, 17590, 17590, 21843, 18836, 18987, 19008, 19233, 20367, 19008, 17173, 30763,
  /*  1545 */ 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452, 21880,
  /*  1560 */ 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008,
  /*  1575 */ 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504,
  /*  1590 */ 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737,
  /*  1605 */ 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481,
  /*  1620 */ 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072,
  /*  1635 */ 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232,
  /*  1650 */ 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535,
  /*  1665 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1680 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1695 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1710 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1725 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1740 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1755 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1770 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1785 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 21696, 18836, 18987, 19008, 19233, 20367, 19008, 17173,
  /*  1800 */ 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452,
  /*  1815 */ 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999,
  /*  1830 */ 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887,
  /*  1845 */ 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730,
  /*  1860 */ 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620,
  /*  1875 */ 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056,
  /*  1890 */ 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403,
  /*  1905 */ 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505,
  /*  1920 */ 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1935 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1950 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1965 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1980 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  1995 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2010 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2025 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2040 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22429, 20131, 18720, 19008, 19233, 20367, 19008,
  /*  2055 */ 17173, 23559, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 18087, 17308, 17327, 17346, 18918,
  /*  2070 */ 18452, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 21242, 19111, 17311, 18658,
  /*  2085 */ 18999, 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585,
  /*  2100 */ 21887, 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176,
  /*  2115 */ 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590,
  /*  2130 */ 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039,
  /*  2145 */ 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807,
  /*  2160 */ 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747,
  /*  2175 */ 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2190 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2205 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2220 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2235 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2250 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2265 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2280 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2295 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 19024, 18836, 18609, 19008, 19233, 20367,
  /*  2310 */ 19008, 17173, 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346,
  /*  2325 */ 18918, 18452, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311,
  /*  2340 */ 18658, 18999, 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559,
  /*  2355 */ 17585, 21887, 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703,
  /*  2370 */ 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832,
  /*  2385 */ 17590, 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621,
  /*  2400 */ 18039, 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376,
  /*  2415 */ 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393,
  /*  2430 */ 18747, 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2445 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2460 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2475 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2490 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2505 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2520 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2535 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2550 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 19081, 22444, 18987, 19008, 19233,
  /*  2565 */ 20367, 19008, 19065, 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327,
  /*  2580 */ 17346, 18918, 18452, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873,
  /*  2595 */ 17311, 18658, 18999, 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543,
  /*  2610 */ 17559, 17585, 21887, 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190,
  /*  2625 */ 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753,
  /*  2640 */ 17832, 17590, 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405,
  /*  2655 */ 18621, 18039, 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312,
  /*  2670 */ 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519,
  /*  2685 */ 17393, 18747, 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2700 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2715 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2730 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2745 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2760 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2775 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2790 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2805 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 21992, 22007, 18987, 19008,
  /*  2820 */ 19233, 20367, 19008, 18690, 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308,
  /*  2835 */ 17327, 17346, 18918, 18452, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127,
  /*  2850 */ 21873, 17311, 18658, 18999, 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326,
  /*  2865 */ 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661,
  /*  2880 */ 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675,
  /*  2895 */ 17753, 17832, 17590, 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681,
  /*  2910 */ 18405, 18621, 18039, 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296,
  /*  2925 */ 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437,
  /*  2940 */ 18519, 17393, 18747, 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2955 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2970 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  2985 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3000 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3015 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3030 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3045 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3060 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22414, 18836, 18987,
  /*  3075 */ 19008, 19233, 30651, 19008, 17173, 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 19138,
  /*  3090 */ 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192,
  /*  3105 */ 18127, 19280, 17311, 18658, 18999, 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714,
  /*  3120 */ 18326, 17543, 17559, 19172, 21887, 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633,
  /*  3135 */ 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892,
  /*  3150 */ 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727,
  /*  3165 */ 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963,
  /*  3180 */ 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421,
  /*  3195 */ 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3210 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3225 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3240 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3255 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3270 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3285 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3300 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3315 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 21783, 18836,
  /*  3330 */ 18987, 19008, 19233, 20367, 19008, 17173, 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355,
  /*  3345 */ 19218, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535,
  /*  3360 */ 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682,
  /*  3375 */ 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217,
  /*  3390 */ 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860,
  /*  3405 */ 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979,
  /*  3420 */ 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266,
  /*  3435 */ 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805,
  /*  3450 */ 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3465 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3480 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3495 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3510 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3525 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3540 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3555 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3570 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 21651,
  /*  3585 */ 18836, 18987, 19008, 19233, 20367, 19008, 17173, 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281,
  /*  3600 */ 20355, 17949, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421,
  /*  3615 */ 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782,
  /*  3630 */ 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467,
  /*  3645 */ 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152,
  /*  3660 */ 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934,
  /*  3675 */ 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239,
  /*  3690 */ 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645,
  /*  3705 */ 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3720 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3735 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3750 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3765 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3780 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3795 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3810 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3825 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3840 */ 19249, 19265, 19307, 18888, 27857, 30536, 24401, 31444, 23357, 18888, 19351, 18888, 18890, 27211, 19370,
  /*  3855 */ 27211, 27211, 19392, 24401, 31911, 24401, 24401, 25467, 18888, 18888, 18888, 18888, 18888, 25783, 27211,
  /*  3870 */ 27211, 27211, 27211, 28537, 19440, 24401, 24401, 24401, 24401, 24036, 17994, 24060, 18888, 18888, 18888,
  /*  3885 */ 18890, 19468, 27211, 27211, 27211, 27211, 19484, 35367, 19520, 24401, 24401, 24401, 19628, 18888, 29855,
  /*  3900 */ 18888, 18888, 23086, 27211, 19538, 27211, 27211, 30756, 24012, 24401, 19560, 24401, 24401, 26750, 18888,
  /*  3915 */ 18888, 19327, 27855, 27211, 27211, 19580, 17590, 24017, 24401, 24401, 19600, 25665, 18888, 18888, 28518,
  /*  3930 */ 27211, 27212, 24016, 19620, 19868, 28435, 25722, 18889, 19644, 27211, 32888, 35852, 19868, 31018, 19694,
  /*  3945 */ 19376, 19717, 22215, 19735, 22098, 19751, 35203, 19776, 19797, 19817, 19840, 25783, 31738, 24135, 19701,
  /*  3960 */ 19856, 31015, 23516, 31008, 28311, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3975 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  3990 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4005 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4020 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4035 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4050 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4065 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4080 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4095 */ 17590, 21768, 18836, 19307, 18888, 27857, 27904, 24401, 29183, 28015, 18888, 18888, 18888, 18890, 27211,
  /*  4110 */ 27211, 27211, 27211, 19888, 24401, 24401, 24401, 24401, 22953, 18888, 18888, 18888, 18888, 18888, 25783,
  /*  4125 */ 27211, 27211, 27211, 27211, 28537, 19440, 24401, 24401, 24401, 24401, 24036, 18881, 18888, 18888, 18888,
  /*  4140 */ 18888, 18890, 27211, 27211, 27211, 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401, 19628, 18888,
  /*  4155 */ 18888, 18888, 18888, 23086, 27211, 27211, 27211, 27211, 30756, 24012, 24401, 24401, 24401, 24401, 26750,
  /*  4170 */ 18888, 18888, 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18887, 18888, 18888,
  /*  4185 */ 27211, 27211, 27212, 24016, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018,
  /*  4200 */ 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837,
  /*  4215 */ 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590,
  /*  4230 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4245 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4260 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4275 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4290 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4305 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4320 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4335 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4350 */ 17590, 17590, 22399, 18836, 19918, 19008, 19233, 20367, 19008, 17173, 30763, 36437, 17330, 17349, 18921,
  /*  4365 */ 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665, 19006, 17265,
  /*  4380 */ 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 32952, 17497, 17520,
  /*  4395 */ 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418, 21915,
  /*  4410 */ 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223,
  /*  4425 */ 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864, 18731, 17918,
  /*  4440 */ 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143, 18706, 18052,
  /*  4455 */ 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392,
  /*  4470 */ 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590, 17590, 17590,
  /*  4485 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4500 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4515 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4530 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4545 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4560 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4575 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4590 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4605 */ 17590, 17590, 17590, 21666, 18836, 19307, 18888, 27857, 27525, 24401, 29183, 21467, 18888, 18888, 18888,
  /*  4620 */ 18890, 27211, 27211, 27211, 27211, 19946, 24401, 24401, 24401, 24401, 32382, 18888, 18888, 18888, 18888,
  /*  4635 */ 18888, 25783, 27211, 27211, 27211, 27211, 28537, 19998, 24401, 24401, 24401, 24401, 31500, 18467, 18888,
  /*  4650 */ 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211, 27211, 20021, 24401, 24401, 24401, 24401, 24401,
  /*  4665 */ 34271, 18888, 18888, 18888, 18888, 23086, 27211, 27211, 27211, 27211, 32926, 29908, 24401, 24401, 24401,
  /*  4680 */ 24401, 26095, 18888, 18888, 18888, 27855, 27211, 27211, 27211, 20050, 22968, 24401, 24401, 24401, 18887,
  /*  4695 */ 18888, 18888, 27211, 27211, 35779, 20080, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889,
  /*  4710 */ 19868, 31018, 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783,
  /*  4725 */ 31738, 19837, 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590,
  /*  4740 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4755 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4770 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4785 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4800 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4815 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4830 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4845 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  4860 */ 17590, 17590, 17590, 17590, 20101, 19039, 20191, 20412, 20903, 17569, 20309, 20872, 25633, 20623, 20505,
  /*  4875 */ 20218, 20242, 17189, 17208, 17281, 20355, 20265, 20306, 20328, 20383, 22490, 20796, 20619, 21354, 20654,
  /*  4890 */ 20410, 20956, 21232, 20765, 17421, 20535, 17192, 18127, 22459, 20312, 25531, 22470, 20309, 20428, 18964,
  /*  4905 */ 20466, 20491, 21342, 21070, 20521, 20682, 17714, 18326, 17543, 17559, 17585, 22497, 20559, 19504, 20279,
  /*  4920 */ 20575, 20290, 20475, 20604, 20639, 20226, 20670, 17661, 21190, 17703, 21176, 17730, 19494, 20698, 20711,
  /*  4935 */ 22480, 21046, 21116, 18971, 21130, 20727, 20755, 17675, 17753, 17832, 17590, 25518, 20394, 20781, 20831,
  /*  4950 */ 20202, 20847, 21401, 17292, 17934, 17979, 18549, 20863, 20588, 25542, 20888, 20919, 18072, 18117, 20935,
  /*  4965 */ 20972, 21032, 21062, 21086, 18239, 21102, 18563, 21146, 21162, 21206, 18351, 20949, 20902, 18340, 21222,
  /*  4980 */ 21258, 21283, 18360, 20249, 17405, 21295, 21311, 21327, 20739, 20343, 21370, 21386, 21417, 17590, 17590,
  /*  4995 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5010 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5025 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5040 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5055 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5070 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5085 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5100 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5115 */ 17590, 17590, 17590, 17590, 17590, 21977, 18836, 18987, 19008, 19233, 20367, 19008, 17173, 30763, 36437,
  /*  5130 */ 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 21452, 21880, 18649,
  /*  5145 */ 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 21504,
  /*  5160 */ 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527,
  /*  5175 */ 17258, 36418, 36501, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 28674, 21946,
  /*  5190 */ 17617, 36473, 18223, 17237, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 21575, 21534, 17481, 19156,
  /*  5205 */ 17864, 18731, 17918, 36551, 17292, 17934, 21560, 30628, 18681, 18405, 18621, 18039, 18056, 18072, 18117,
  /*  5220 */ 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796,
  /*  5235 */ 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590,
  /*  5250 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5265 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5280 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5295 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5310 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5325 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5340 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5355 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5370 */ 17590, 17590, 17590, 17590, 17590, 17590, 21798, 18836, 21612, 19008, 19233, 20367, 19008, 17173, 30763,
  /*  5385 */ 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452, 21880,
  /*  5400 */ 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008,
  /*  5415 */ 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504,
  /*  5430 */ 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737,
  /*  5445 */ 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481,
  /*  5460 */ 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072,
  /*  5475 */ 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232,
  /*  5490 */ 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535,
  /*  5505 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5520 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5535 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5550 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5565 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5580 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5595 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5610 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5625 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 21636, 18836, 18987, 19008, 19233, 17902, 19008, 17173,
  /*  5640 */ 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452,
  /*  5655 */ 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999,
  /*  5670 */ 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887,
  /*  5685 */ 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730,
  /*  5700 */ 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620,
  /*  5715 */ 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056,
  /*  5730 */ 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403,
  /*  5745 */ 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505,
  /*  5760 */ 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5775 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5790 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5805 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5820 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5835 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5850 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5865 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  5880 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 21753, 19096, 21903, 19008, 19233, 20367, 19008,
  /*  5895 */ 19291, 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918,
  /*  5910 */ 17379, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658,
  /*  5925 */ 18999, 19008, 17447, 21931, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585,
  /*  5940 */ 21887, 17504, 17527, 17258, 36418, 18280, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176,
  /*  5955 */ 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590,
  /*  5970 */ 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039,
  /*  5985 */ 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807,
  /*  6000 */ 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747,
  /*  6015 */ 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6030 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6045 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6060 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6075 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6090 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6105 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6120 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6135 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 21962, 18594, 18987, 19008, 19233, 22043,
  /*  6150 */ 19008, 17173, 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346,
  /*  6165 */ 18918, 18452, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311,
  /*  6180 */ 18658, 18999, 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559,
  /*  6195 */ 17585, 21887, 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703,
  /*  6210 */ 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832,
  /*  6225 */ 17590, 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621,
  /*  6240 */ 18039, 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376,
  /*  6255 */ 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393,
  /*  6270 */ 18747, 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6285 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6300 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6315 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6330 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6345 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6360 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6375 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6390 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 21681, 21858, 18987, 19008, 19233,
  /*  6405 */ 20367, 19008, 21544, 30763, 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327,
  /*  6420 */ 17346, 18918, 18452, 21880, 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873,
  /*  6435 */ 17311, 18658, 18999, 19008, 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543,
  /*  6450 */ 17559, 17585, 21887, 17504, 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190,
  /*  6465 */ 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753,
  /*  6480 */ 17832, 17590, 21620, 17481, 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405,
  /*  6495 */ 18621, 18039, 18056, 18072, 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312,
  /*  6510 */ 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519,
  /*  6525 */ 17393, 18747, 18505, 18535, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6540 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6555 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6570 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6585 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6600 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6615 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6630 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6645 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22339, 18836, 22059, 18888,
  /*  6660 */ 27857, 34097, 24401, 29183, 22087, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211, 22121, 24401,
  /*  6675 */ 24401, 24401, 24401, 30613, 18888, 18888, 18888, 18888, 18888, 25783, 27211, 27211, 27211, 27211, 35072,
  /*  6690 */ 22164, 24401, 24401, 24401, 24401, 31500, 31693, 18888, 18888, 18888, 18888, 18890, 27211, 27211, 27211,
  /*  6705 */ 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401, 32319, 18888, 18888, 18888, 18888, 23086, 27211,
  /*  6720 */ 27211, 27211, 27211, 30756, 21431, 24401, 24401, 24401, 24401, 26095, 18888, 18888, 18888, 27855, 27211,
  /*  6735 */ 27211, 27211, 22187, 22968, 24401, 24401, 24401, 22231, 18888, 18888, 27211, 27211, 35779, 20080, 24402,
  /*  6750 */ 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890, 27211, 31833, 19406, 19447,
  /*  6765 */ 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760, 31015, 23516, 31008,
  /*  6780 */ 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6795 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6810 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6825 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6840 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6855 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6870 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6885 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  6900 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22339, 18836, 22059,
  /*  6915 */ 18888, 27857, 34097, 24401, 29183, 22087, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211, 22121,
  /*  6930 */ 24401, 24401, 24401, 24401, 30613, 18888, 18888, 18888, 18888, 18888, 25783, 27211, 27211, 27211, 27211,
  /*  6945 */ 35072, 22164, 24401, 24401, 24401, 24401, 31500, 31693, 18888, 18888, 18888, 18888, 18890, 27211, 27211,
  /*  6960 */ 27211, 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401, 31181, 18888, 18888, 18888, 18888, 23086,
  /*  6975 */ 27211, 27211, 27211, 27211, 30756, 21431, 24401, 24401, 24401, 24401, 26095, 18888, 18888, 18888, 27855,
  /*  6990 */ 27211, 27211, 27211, 22187, 22968, 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211, 35779, 20080,
  /*  7005 */ 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890, 27211, 31833, 19406,
  /*  7020 */ 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760, 31015, 23516,
  /*  7035 */ 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7050 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7065 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7080 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7095 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7110 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7125 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7140 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7155 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22339, 18836,
  /*  7170 */ 22059, 18888, 27857, 34097, 24401, 29183, 22087, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211,
  /*  7185 */ 22121, 24401, 24401, 24401, 24401, 31678, 18888, 18888, 18888, 18888, 18888, 25783, 27211, 27211, 27211,
  /*  7200 */ 27211, 35072, 22164, 24401, 24401, 24401, 24401, 31500, 31693, 18888, 18888, 18888, 18888, 18890, 27211,
  /*  7215 */ 27211, 27211, 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401, 31181, 18888, 18888, 18888, 18888,
  /*  7230 */ 23086, 27211, 27211, 27211, 27211, 30756, 21431, 24401, 24401, 24401, 24401, 26095, 18888, 18888, 18888,
  /*  7245 */ 27855, 27211, 27211, 27211, 22187, 22968, 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211, 35779,
  /*  7260 */ 20080, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890, 27211, 31833,
  /*  7275 */ 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760, 31015,
  /*  7290 */ 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7305 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7320 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7335 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7350 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7365 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7380 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7395 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7410 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22339,
  /*  7425 */ 18836, 22059, 18888, 27857, 34097, 24401, 29183, 22087, 18888, 18888, 18888, 18890, 27211, 27211, 27211,
  /*  7440 */ 27211, 22121, 24401, 24401, 24401, 24401, 30613, 18888, 18888, 18888, 18888, 18888, 25783, 27211, 27211,
  /*  7455 */ 27211, 27211, 35072, 22164, 24401, 24401, 24401, 24401, 33588, 31693, 18888, 18888, 18888, 18888, 18890,
  /*  7470 */ 27211, 27211, 27211, 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401, 31181, 18888, 18888, 18888,
  /*  7485 */ 18888, 23086, 27211, 27211, 27211, 27211, 30756, 21431, 24401, 24401, 24401, 24401, 26095, 18888, 18888,
  /*  7500 */ 18888, 27855, 27211, 27211, 27211, 22187, 22968, 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211,
  /*  7515 */ 35779, 20080, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890, 27211,
  /*  7530 */ 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760,
  /*  7545 */ 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7560 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7575 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7590 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7605 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7620 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7635 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7650 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7665 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7680 */ 22339, 18836, 22059, 18888, 27857, 35019, 24401, 29183, 22087, 18888, 18888, 18888, 18890, 27211, 27211,
  /*  7695 */ 27211, 27211, 22248, 24401, 24401, 24401, 24401, 30613, 18888, 18888, 18888, 18888, 18888, 25783, 27211,
  /*  7710 */ 27211, 27211, 27211, 35072, 22164, 24401, 24401, 24401, 24401, 31500, 31693, 18888, 18888, 18888, 18888,
  /*  7725 */ 18890, 27211, 27211, 27211, 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401, 31181, 18888, 18888,
  /*  7740 */ 18888, 18888, 23086, 27211, 27211, 27211, 27211, 30756, 21431, 24401, 24401, 24401, 24401, 26095, 18888,
  /*  7755 */ 18888, 18888, 27855, 27211, 27211, 27211, 22187, 22968, 24401, 24401, 24401, 18887, 18888, 18888, 27211,
  /*  7770 */ 27211, 35779, 20080, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890,
  /*  7785 */ 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782,
  /*  7800 */ 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7815 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7830 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7845 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7860 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7875 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7890 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7905 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7920 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  7935 */ 17590, 22339, 18836, 22059, 18888, 27857, 34097, 24401, 29183, 22087, 18888, 18888, 18888, 18890, 27211,
  /*  7950 */ 27211, 27211, 27211, 22121, 24401, 24401, 24401, 24401, 18866, 18888, 18888, 18888, 18888, 18888, 25783,
  /*  7965 */ 27211, 27211, 27211, 27211, 35072, 22164, 24401, 24401, 24401, 24401, 24036, 31693, 18888, 18888, 18888,
  /*  7980 */ 18888, 18890, 27211, 27211, 27211, 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401, 19628, 18888,
  /*  7995 */ 18888, 18888, 18888, 23086, 27211, 27211, 27211, 27211, 30756, 24012, 24401, 24401, 24401, 24401, 26750,
  /*  8010 */ 18888, 18888, 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18887, 18888, 18888,
  /*  8025 */ 27211, 27211, 27212, 24016, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018,
  /*  8040 */ 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837,
  /*  8055 */ 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590,
  /*  8070 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8085 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8100 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8115 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8130 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8145 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8160 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8175 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8190 */ 17590, 17590, 22324, 18836, 22059, 18888, 27857, 30501, 24401, 29183, 22087, 18888, 18888, 18888, 18890,
  /*  8205 */ 27211, 27211, 27211, 27211, 22121, 24401, 24401, 24401, 24401, 18866, 18888, 18888, 18888, 18888, 18888,
  /*  8220 */ 25783, 27211, 27211, 27211, 27211, 35072, 22164, 24401, 24401, 24401, 24401, 24036, 31693, 18888, 18888,
  /*  8235 */ 18888, 18888, 18890, 27211, 27211, 27211, 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401, 19628,
  /*  8250 */ 18888, 18888, 18888, 18888, 23086, 27211, 27211, 27211, 27211, 30756, 24012, 24401, 24401, 24401, 24401,
  /*  8265 */ 26750, 18888, 18888, 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18887, 18888,
  /*  8280 */ 18888, 27211, 27211, 27212, 24016, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868,
  /*  8295 */ 31018, 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738,
  /*  8310 */ 19837, 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590,
  /*  8325 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8340 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8355 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8370 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8385 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8400 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8415 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8430 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8445 */ 17590, 17590, 17590, 22339, 18836, 22059, 18888, 27857, 34097, 24401, 29183, 22087, 18888, 18888, 18888,
  /*  8460 */ 18890, 27211, 27211, 27211, 27211, 22121, 24401, 24401, 24401, 24401, 18866, 18888, 18888, 18888, 18888,
  /*  8475 */ 18888, 25783, 27211, 27211, 27211, 27211, 35072, 22164, 24401, 24401, 24401, 24401, 24036, 31693, 18888,
  /*  8490 */ 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401,
  /*  8505 */ 19628, 18888, 18888, 18888, 18888, 23086, 27211, 27211, 27211, 27211, 30756, 24012, 24401, 24401, 24401,
  /*  8520 */ 24401, 34365, 18888, 18888, 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18887,
  /*  8535 */ 18888, 18888, 27211, 27211, 27212, 24016, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889,
  /*  8550 */ 19868, 31018, 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783,
  /*  8565 */ 31738, 19837, 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590,
  /*  8580 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8595 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8610 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8625 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8640 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8655 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8670 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8685 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8700 */ 17590, 17590, 17590, 17590, 22354, 18836, 18987, 19008, 19233, 20367, 19008, 17173, 27086, 36437, 17330,
  /*  8715 */ 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665,
  /*  8730 */ 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 32952,
  /*  8745 */ 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258,
  /*  8760 */ 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617,
  /*  8775 */ 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864,
  /*  8790 */ 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 19930, 18039, 18056, 18072, 18117, 18143,
  /*  8805 */ 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163,
  /*  8820 */ 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590,
  /*  8835 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8850 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8865 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8880 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8895 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8910 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8925 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8940 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  8955 */ 17590, 17590, 17590, 17590, 17590, 21828, 18836, 18987, 19008, 19233, 20367, 19008, 17173, 30763, 36437,
  /*  8970 */ 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452, 21880, 18649,
  /*  8985 */ 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447,
  /*  9000 */ 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527,
  /*  9015 */ 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946,
  /*  9030 */ 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156,
  /*  9045 */ 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117,
  /*  9060 */ 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796,
  /*  9075 */ 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590,
  /*  9090 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9105 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9120 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9135 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9150 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9165 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9180 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9195 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9210 */ 17590, 17590, 17590, 17590, 17590, 17590, 22309, 22513, 18987, 19008, 19233, 20367, 19008, 19122, 30763,
  /*  9225 */ 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 22544, 21880,
  /*  9240 */ 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008,
  /*  9255 */ 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504,
  /*  9270 */ 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737,
  /*  9285 */ 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481,
  /*  9300 */ 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072,
  /*  9315 */ 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232,
  /*  9330 */ 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535,
  /*  9345 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9360 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9375 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9390 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9405 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9420 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9435 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9450 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9465 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22608, 18836, 22988, 23004, 27585, 23020, 23036, 23067,
  /*  9480 */ 22087, 18888, 18888, 18888, 23083, 27211, 27211, 27211, 23102, 22121, 24401, 24401, 24401, 23122, 31386,
  /*  9495 */ 26154, 19674, 18888, 28119, 28232, 19424, 23705, 27211, 27211, 23142, 23173, 23189, 23212, 24401, 24401,
  /*  9510 */ 23246, 34427, 31693, 23262, 18888, 23290, 23308, 27783, 27620, 23327, 35263, 35107, 33383, 23346, 18193,
  /*  9525 */ 23393, 32748, 23968, 24401, 23414, 35153, 23463, 18888, 33913, 23442, 23482, 27211, 27211, 23532, 23552,
  /*  9540 */ 21431, 23575, 24401, 24401, 23604, 26095, 23635, 23657, 18888, 33482, 23685, 33251, 27211, 22187, 18851,
  /*  9555 */ 23721, 35536, 24401, 18887, 23750, 32641, 27211, 23769, 23787, 20080, 33012, 24384, 25659, 18888, 18889,
  /*  9570 */ 27211, 27211, 19719, 23889, 23803, 31018, 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 28224,
  /*  9585 */ 31826, 23823, 26917, 34978, 23850, 26493, 25782, 23878, 23914, 23516, 31008, 22105, 19419, 27963, 19659,
  /*  9600 */ 29781, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9615 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9630 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9645 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9660 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9675 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9690 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9705 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9720 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22623, 18836, 22059, 18888, 27857, 34097, 24401,
  /*  9735 */ 29183, 22087, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211, 22121, 24401, 24401, 24401, 24401,
  /*  9750 */ 30613, 18888, 18888, 18888, 18888, 28909, 25783, 27211, 27211, 27211, 34048, 23933, 22164, 24401, 24401,
  /*  9765 */ 24401, 28409, 23949, 31693, 18888, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211, 27211, 19484,
  /*  9780 */ 24401, 24401, 24401, 24401, 24401, 31181, 26583, 18888, 18888, 18888, 35585, 23984, 27211, 27211, 27211,
  /*  9795 */ 24005, 22201, 24033, 24401, 24401, 24401, 24052, 18888, 18888, 18888, 27855, 27211, 27211, 27211, 22187,
  /*  9810 */ 22968, 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211, 35779, 20080, 24402, 19868, 25659, 18888,
  /*  9825 */ 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828,
  /*  9840 */ 31017, 27856, 31741, 26496, 24076, 24126, 24151, 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963,
  /*  9855 */ 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9870 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9885 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9900 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9915 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9930 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9945 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9960 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /*  9975 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22638, 18836, 22059, 19678, 27857, 24185,
  /*  9990 */ 24401, 24201, 24217, 26592, 18888, 18888, 18890, 24252, 24268, 27211, 27211, 22121, 24287, 24303, 24401,
  /* 10005 */ 24401, 30613, 19781, 35432, 36007, 32649, 18888, 25783, 24322, 28966, 23771, 27211, 35072, 22164, 24358,
  /* 10020 */ 32106, 26829, 24400, 31500, 31693, 18888, 18888, 18888, 24801, 18890, 27211, 27211, 27211, 27211, 24418,
  /* 10035 */ 19484, 24401, 24401, 24401, 24401, 20167, 31181, 18888, 18888, 18888, 27833, 23086, 27211, 27211, 33540,
  /* 10050 */ 27211, 30756, 21431, 24401, 24401, 22972, 24401, 26095, 18888, 36131, 18888, 27855, 27211, 24440, 27211,
  /* 10065 */ 22187, 22968, 24401, 24459, 24401, 31699, 28454, 18888, 34528, 34570, 35779, 24478, 24402, 24494, 25659,
  /* 10080 */ 18888, 36228, 27211, 27211, 24515, 30981, 23734, 31018, 18890, 27211, 31833, 19406, 19447, 23086, 23330,
  /* 10095 */ 24538, 31017, 27856, 31741, 30059, 23377, 24563, 19837, 25782, 19760, 31015, 23516, 25374, 22105, 19419,
  /* 10110 */ 29793, 24579, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10125 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10140 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10155 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10170 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10185 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10200 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10215 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10230 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22653, 18836, 22059, 25756, 19982,
  /* 10245 */ 34097, 23196, 29183, 24614, 24110, 23641, 24673, 26103, 24697, 24443, 24713, 28558, 22121, 24748, 24462,
  /* 10260 */ 24764, 23398, 30613, 18888, 18888, 18888, 18888, 24798, 25783, 27211, 27211, 27211, 34232, 35072, 22164,
  /* 10275 */ 24401, 24401, 24401, 33302, 31500, 22559, 24106, 24232, 18888, 18888, 34970, 24817, 30411, 27211, 27211,
  /* 10290 */ 32484, 19484, 29750, 35127, 24401, 24401, 19872, 31181, 24852, 18888, 18888, 24871, 29221, 27211, 27211,
  /* 10305 */ 32072, 27211, 30756, 34441, 24401, 24401, 31571, 24401, 26095, 33141, 27802, 27011, 27855, 25295, 25607,
  /* 10320 */ 24888, 22187, 22968, 19195, 34593, 24906, 18887, 18888, 18888, 27211, 27211, 35779, 20080, 24402, 19868,
  /* 10335 */ 25659, 18888, 33663, 27211, 27211, 24924, 24947, 23588, 31018, 18890, 27211, 31833, 22135, 19447, 23086,
  /* 10350 */ 23330, 19828, 30904, 31042, 24972, 19840, 25000, 31738, 30898, 25782, 19760, 31015, 23516, 31008, 22105,
  /* 10365 */ 19419, 25016, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10380 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10395 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10410 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10425 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10440 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10455 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10470 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10485 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22668, 18836, 25041, 25057,
  /* 10500 */ 31320, 25073, 25089, 25105, 22087, 34796, 24236, 36138, 34870, 34125, 25121, 23106, 35497, 22248, 36613,
  /* 10515 */ 25137, 30671, 27365, 30613, 25153, 26447, 25199, 25233, 22574, 23274, 25249, 25265, 25281, 25318, 25344,
  /* 10530 */ 25360, 25400, 25428, 25452, 26731, 25504, 31693, 23669, 25558, 27407, 25575, 28599, 25934, 25599, 27211,
  /* 10545 */ 28180, 27304, 25623, 25839, 25649, 24401, 34820, 25681, 25698, 22586, 27775, 30190, 25745, 25778, 25799,
  /* 10560 */ 25817, 28995, 33569, 30756, 21518, 33443, 25837, 25855, 25893, 26095, 31254, 26677, 30136, 27855, 25930,
  /* 10575 */ 25950, 27211, 22187, 22968, 25966, 25986, 24401, 23428, 27763, 36330, 26959, 26002, 26029, 26045, 26085,
  /* 10590 */ 26119, 26170, 26203, 26222, 26239, 30527, 26372, 26274, 28404, 31018, 33757, 27211, 34262, 26316, 36729,
  /* 10605 */ 26345, 26366, 35337, 31017, 26388, 26407, 30954, 26350, 33861, 26434, 26463, 26479, 26512, 23516, 33189,
  /* 10620 */ 26531, 26547, 27963, 31293, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10635 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10650 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10665 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10680 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10695 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10710 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10725 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10740 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22683, 18836, 26568,
  /* 10755 */ 26181, 26608, 34097, 26643, 29183, 22087, 26669, 18888, 18888, 18890, 26693, 27211, 27211, 27211, 22121,
  /* 10770 */ 26720, 24401, 24401, 24401, 30613, 18888, 18888, 18888, 18888, 26774, 25783, 27211, 27211, 27211, 26619,
  /* 10785 */ 35072, 22164, 24401, 24401, 24401, 21596, 31500, 31693, 18888, 18888, 33978, 18888, 18890, 27211, 27211,
  /* 10800 */ 25801, 27211, 27211, 19484, 24401, 24401, 24401, 26792, 24401, 31181, 18888, 18888, 18888, 35464, 23086,
  /* 10815 */ 27211, 27211, 27211, 26809, 30756, 21431, 24401, 24401, 24401, 26828, 26095, 18888, 18888, 18888, 27855,
  /* 10830 */ 27211, 27211, 27211, 22187, 22968, 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211, 35779, 20080,
  /* 10845 */ 24402, 19868, 25659, 31948, 18889, 35707, 27211, 19719, 26845, 19868, 31018, 18890, 27211, 31833, 19406,
  /* 10860 */ 19447, 23086, 23330, 26905, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760, 31015, 23516,
  /* 10875 */ 24984, 31088, 19419, 26945, 27651, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10890 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10905 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10920 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10935 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10950 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10965 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10980 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 10995 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22698, 18836,
  /* 11010 */ 26999, 18888, 27857, 34097, 24401, 29183, 22087, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211,
  /* 11025 */ 22121, 24401, 24401, 24401, 24401, 23051, 18888, 18888, 18888, 18888, 18888, 25783, 27211, 27211, 27211,
  /* 11040 */ 27211, 35072, 27033, 24401, 24401, 24401, 24401, 24036, 31693, 18888, 18888, 27056, 18888, 18890, 27211,
  /* 11055 */ 27211, 30320, 27211, 27211, 27075, 24401, 24401, 29032, 24401, 24401, 19628, 18888, 18888, 18888, 18888,
  /* 11070 */ 23086, 27211, 27211, 27211, 27211, 30756, 24012, 24401, 24401, 24401, 24401, 26750, 18888, 18888, 33986,
  /* 11085 */ 27855, 27211, 27211, 27102, 17590, 24017, 24401, 24401, 27123, 27144, 36254, 27162, 27210, 27228, 28500,
  /* 11100 */ 18187, 34842, 33426, 27244, 35980, 27277, 27302, 27320, 36048, 34013, 20999, 31882, 21478, 27895, 27356,
  /* 11115 */ 30287, 27381, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760, 31015,
  /* 11130 */ 23516, 31008, 22105, 26329, 30087, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11145 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11160 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11175 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11190 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11205 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11220 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11235 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11250 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22339,
  /* 11265 */ 18836, 22059, 27406, 27423, 27445, 35294, 27461, 22087, 18888, 18888, 30140, 18890, 27211, 27211, 27989,
  /* 11280 */ 27211, 22121, 24401, 24401, 25682, 24401, 18866, 18888, 18888, 18888, 18888, 18888, 34042, 27211, 27211,
  /* 11295 */ 27211, 27211, 29700, 22164, 24401, 24401, 24401, 24401, 27128, 31693, 27477, 18888, 18888, 18888, 18890,
  /* 11310 */ 27194, 27211, 27211, 27211, 27211, 19484, 35299, 24401, 24401, 24401, 24401, 19628, 18888, 18888, 18888,
  /* 11325 */ 27059, 23086, 27211, 27211, 27211, 33366, 30756, 24012, 24401, 24401, 24401, 35044, 26750, 18888, 18888,
  /* 11340 */ 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211,
  /* 11355 */ 27212, 24016, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018, 20815, 27211,
  /* 11370 */ 30818, 19960, 33969, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760,
  /* 11385 */ 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11400 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11415 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11430 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11445 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11460 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11475 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11490 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11505 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11520 */ 22713, 18836, 22059, 27496, 27516, 27541, 35231, 27557, 22087, 29662, 26292, 23292, 27573, 24836, 27601,
  /* 11535 */ 27211, 27636, 22121, 35544, 27686, 24401, 27721, 18866, 18888, 27799, 18888, 27818, 22071, 27853, 32260,
  /* 11550 */ 27211, 26013, 27873, 27920, 22164, 29419, 24401, 29946, 33413, 26742, 27751, 26881, 18888, 18888, 27261,
  /* 11565 */ 36776, 27936, 27211, 27211, 27211, 27988, 28005, 28031, 28052, 24401, 24401, 28069, 28088, 28135, 25488,
  /* 11580 */ 28152, 26069, 28167, 27211, 28340, 24657, 28196, 30756, 31523, 24401, 28212, 34176, 36174, 24956, 28248,
  /* 11595 */ 28266, 28290, 21488, 33077, 28327, 28356, 17590, 20986, 23126, 28391, 28425, 28102, 28451, 28470, 28490,
  /* 11610 */ 28516, 28534, 20034, 33728, 25868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 30241, 28274,
  /* 11625 */ 28553, 28574, 19406, 28590, 23086, 23330, 19828, 19452, 28615, 28660, 26147, 25783, 31738, 19837, 25782,
  /* 11640 */ 19760, 29613, 35958, 29276, 22105, 19419, 27963, 23157, 28700, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11655 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11670 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11685 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11700 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11715 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11730 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11745 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11760 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11775 */ 17590, 22339, 18836, 22059, 18888, 27857, 34097, 24401, 29183, 22087, 18888, 18888, 18888, 18890, 27211,
  /* 11790 */ 27211, 27211, 27211, 22121, 24401, 24401, 24401, 24401, 18866, 18888, 18888, 18888, 18888, 18888, 25783,
  /* 11805 */ 27211, 27211, 27211, 27211, 35072, 22164, 24401, 24401, 24401, 24401, 24036, 22528, 18888, 18888, 18888,
  /* 11820 */ 18888, 18890, 27333, 27211, 27211, 27211, 27211, 19484, 30853, 24401, 24401, 24401, 24401, 19628, 18888,
  /* 11835 */ 18888, 18888, 18888, 23086, 27211, 27211, 27211, 27211, 30756, 24012, 24401, 24401, 24401, 24401, 26750,
  /* 11850 */ 18888, 18888, 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18887, 18888, 18888,
  /* 11865 */ 27211, 27211, 27212, 24016, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018,
  /* 11880 */ 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837,
  /* 11895 */ 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590,
  /* 11910 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11925 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11940 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11955 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11970 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 11985 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12000 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12015 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12030 */ 17590, 17590, 22728, 18836, 28747, 28782, 28817, 28841, 28857, 28880, 28896, 24161, 28943, 32011, 36261,
  /* 12045 */ 27340, 28961, 29492, 28982, 29011, 24522, 29027, 25436, 29048, 23051, 27500, 29090, 29110, 30713, 18888,
  /* 12060 */ 23512, 29130, 25183, 27211, 29155, 28927, 27033, 29173, 23230, 24401, 29199, 35373, 31693, 18888, 18888,
  /* 12075 */ 25583, 32629, 29218, 27211, 27211, 31461, 30692, 29237, 27075, 24401, 24401, 24401, 29262, 29302, 19628,
  /* 12090 */ 18888, 34329, 18888, 18888, 23086, 27211, 29329, 27211, 27211, 30756, 24012, 35933, 24401, 24401, 24401,
  /* 12105 */ 27705, 31612, 18888, 18888, 29346, 29374, 27211, 35650, 17590, 21436, 29393, 24401, 25970, 18887, 33895,
  /* 12120 */ 18888, 27211, 32528, 27212, 24016, 32769, 19868, 25659, 18888, 26889, 27211, 27211, 29412, 23889, 24371,
  /* 12135 */ 31018, 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31768, 19840, 25783, 31738,
  /* 12150 */ 19837, 29435, 29508, 31102, 29550, 29606, 22105, 30300, 29462, 19659, 27951, 17590, 17590, 17590, 17590,
  /* 12165 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12180 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12195 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12210 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12225 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12240 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12255 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12270 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12285 */ 17590, 17590, 17590, 22743, 18836, 22059, 29629, 29473, 34097, 33285, 29183, 29651, 27254, 18888, 29678,
  /* 12300 */ 33329, 32535, 27211, 29694, 29716, 22121, 19202, 24401, 32742, 29741, 18866, 26776, 33921, 28474, 18888,
  /* 12315 */ 18888, 25783, 29766, 27211, 29809, 27211, 35072, 22164, 35825, 24401, 29828, 24401, 24036, 36769, 25217,
  /* 12330 */ 18888, 18888, 29848, 18890, 27211, 29871, 27211, 26258, 27211, 29894, 24401, 29929, 24401, 36587, 24401,
  /* 12345 */ 19628, 18888, 18888, 18888, 18888, 23086, 27211, 27211, 27211, 27211, 29725, 29962, 24401, 24401, 24401,
  /* 12360 */ 24401, 26750, 18888, 18888, 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18473,
  /* 12375 */ 18888, 18888, 19584, 27211, 27212, 24016, 29982, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889,
  /* 12390 */ 19868, 31018, 18890, 27211, 31833, 19902, 19447, 32052, 19544, 19828, 29998, 30097, 30031, 19840, 25783,
  /* 12405 */ 30047, 19837, 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 30075, 17590, 17590, 17590,
  /* 12420 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12435 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12450 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12465 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12480 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12495 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12510 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12525 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12540 */ 17590, 17590, 17590, 17590, 22758, 18836, 30121, 30156, 30206, 30257, 30273, 30336, 22087, 35624, 32837,
  /* 12555 */ 25762, 18890, 29878, 34934, 26812, 27211, 22121, 24931, 23223, 29202, 24401, 18866, 34373, 30352, 18888,
  /* 12570 */ 18888, 18888, 23447, 24828, 27211, 27211, 27211, 35072, 30370, 35052, 24401, 24401, 24401, 24036, 29523,
  /* 12585 */ 18888, 18888, 27146, 18888, 31308, 30386, 27211, 27211, 30405, 30558, 19484, 30427, 24401, 24401, 29938,
  /* 12600 */ 35686, 19628, 28766, 30447, 34506, 35614, 23086, 28731, 30482, 30517, 30552, 30756, 24012, 20156, 30574,
  /* 12615 */ 30598, 30667, 26283, 33464, 28945, 27670, 30687, 32915, 33504, 25328, 17590, 23963, 20450, 33837, 21016,
  /* 12630 */ 32397, 26300, 30708, 30729, 27885, 30748, 21588, 36373, 30779, 26653, 24628, 33220, 32514, 30806, 31835,
  /* 12645 */ 25412, 25906, 26515, 18890, 28825, 31833, 26133, 19447, 28304, 31730, 23834, 26057, 30869, 30885, 32181,
  /* 12660 */ 30920, 30942, 32797, 25782, 30970, 31015, 23516, 31008, 30997, 31034, 27963, 19659, 29450, 17590, 17590,
  /* 12675 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12690 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12705 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12720 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12735 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12750 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12765 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12780 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12795 */ 17590, 17590, 17590, 17590, 17590, 22773, 18836, 31058, 31074, 32463, 31125, 31141, 31197, 22087, 18888,
  /* 12810 */ 29534, 35471, 36738, 27211, 24342, 31213, 24424, 22121, 24401, 20175, 31229, 31917, 27736, 31245, 34334,
  /* 12825 */ 27175, 18888, 29094, 27286, 27211, 31278, 31336, 27211, 31355, 31371, 24401, 31402, 31418, 24401, 31437,
  /* 12840 */ 31693, 18888, 31619, 32841, 18888, 18890, 27211, 27211, 31460, 31477, 27211, 19484, 24401, 24401, 31497,
  /* 12855 */ 36581, 24401, 33020, 18888, 18888, 18888, 18888, 30007, 27211, 27211, 27211, 27211, 31516, 32310, 24401,
  /* 12870 */ 24401, 24401, 24401, 31539, 18888, 28762, 18888, 24651, 35740, 27211, 27211, 28644, 31565, 35796, 24401,
  /* 12885 */ 24401, 19318, 32188, 18888, 24334, 28366, 27212, 29966, 29832, 19868, 25659, 18888, 18889, 27211, 27211,
  /* 12900 */ 19719, 31587, 19868, 31635, 32435, 33693, 30105, 31663, 20005, 31715, 31757, 31784, 31812, 30015, 31851,
  /* 12915 */ 31878, 25783, 31898, 19837, 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 31933, 30221, 17590,
  /* 12930 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12945 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12960 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12975 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 12990 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13005 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13020 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13035 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13050 */ 17590, 17590, 17590, 17590, 17590, 17590, 22788, 18836, 22059, 25729, 30466, 31968, 24306, 31984, 32000,
  /* 13065 */ 32807, 35160, 27017, 29590, 34941, 19801, 29377, 33700, 22121, 27040, 30431, 29396, 28864, 29565, 18888,
  /* 13080 */ 18888, 18888, 32027, 18888, 25783, 27211, 27211, 23698, 27211, 35072, 22164, 24401, 24401, 30845, 24401,
  /* 13095 */ 24036, 32045, 18888, 26929, 18888, 18888, 18890, 27211, 31481, 32068, 27211, 27211, 32088, 24401, 33058,
  /* 13110 */ 32122, 24401, 24401, 33736, 18888, 18888, 33162, 18888, 23086, 27211, 27211, 29484, 27211, 28375, 32144,
  /* 13125 */ 24401, 24401, 33831, 24401, 26750, 18888, 18888, 18888, 27855, 27211, 27211, 27211, 36704, 24017, 24401,
  /* 13140 */ 24401, 24401, 18887, 18888, 18888, 27211, 27211, 27212, 24016, 24402, 19868, 25659, 18888, 18889, 27211,
  /* 13155 */ 27211, 19719, 23889, 19868, 31018, 18890, 27211, 31833, 33107, 22171, 33224, 24271, 32169, 31017, 27856,
  /* 13170 */ 31741, 19840, 25783, 31738, 30234, 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951,
  /* 13185 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13200 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13215 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13230 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13245 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13260 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13275 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13290 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13305 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22339, 18836, 32204, 32232, 32252, 32677, 33295, 29074,
  /* 13320 */ 22087, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211, 22121, 24401, 24401, 24401, 24401, 23619,
  /* 13335 */ 18888, 18888, 18888, 18888, 18888, 25783, 27211, 27211, 27211, 27211, 35072, 32276, 24401, 24401, 24401,
  /* 13350 */ 24401, 24036, 31693, 18888, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211, 27211, 32299, 24401,
  /* 13365 */ 24401, 24401, 24401, 24401, 19628, 18888, 18888, 18888, 18888, 23086, 27211, 27211, 27211, 27211, 30756,
  /* 13380 */ 24012, 24401, 24401, 24401, 24401, 26750, 18888, 18888, 18888, 27855, 27211, 27211, 27211, 17590, 24017,
  /* 13395 */ 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211, 27212, 24016, 24402, 19868, 25659, 33886, 18889,
  /* 13410 */ 36065, 27211, 19719, 35326, 19868, 31018, 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017,
  /* 13425 */ 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659,
  /* 13440 */ 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13455 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13470 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13485 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13500 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13515 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13530 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13545 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13560 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22803, 18836, 32335, 31647, 34666, 32351, 32367,
  /* 13575 */ 32417, 22087, 18888, 32433, 19335, 32451, 27211, 32479, 27107, 32500, 22121, 24401, 32551, 20085, 32572,
  /* 13590 */ 18866, 22287, 23753, 18888, 18888, 32602, 32665, 27211, 32693, 27211, 26972, 32713, 32729, 24401, 32764,
  /* 13605 */ 24401, 25877, 32785, 34768, 18888, 27390, 32823, 24594, 24855, 32857, 24890, 32878, 32904, 27211, 32942,
  /* 13620 */ 32977, 24401, 33000, 29313, 24401, 30790, 26206, 27666, 33904, 18888, 23086, 36353, 27211, 33036, 27211,
  /* 13635 */ 30756, 24012, 32153, 24401, 33056, 24401, 35861, 18888, 18888, 30354, 27972, 27211, 27211, 33800, 17590,
  /* 13650 */ 20145, 24401, 24401, 34638, 20811, 18888, 18888, 33074, 27211, 27212, 36167, 24402, 19868, 25659, 18888,
  /* 13665 */ 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890, 27211, 31833, 19406, 34616, 24169, 33093, 33123,
  /* 13680 */ 33157, 27856, 31741, 23862, 26552, 34302, 19837, 25782, 19760, 31015, 23516, 31008, 33178, 19973, 27963,
  /* 13695 */ 23497, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13710 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13725 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13740 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13755 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13770 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13785 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13800 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13815 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22818, 18836, 33205, 28113, 33240, 34097,
  /* 13830 */ 33275, 29183, 22087, 33318, 35438, 18888, 18890, 33345, 26391, 33382, 27211, 22121, 33399, 28072, 33442,
  /* 13845 */ 24401, 18866, 22232, 18888, 33459, 18888, 18888, 33480, 33498, 25175, 27211, 27211, 26704, 22164, 24775,
  /* 13860 */ 35239, 24401, 24401, 25914, 29580, 18888, 18888, 31109, 25211, 33520, 33539, 27211, 27211, 33556, 36284,
  /* 13875 */ 19484, 33585, 24401, 24401, 33604, 32556, 19628, 18888, 18888, 31262, 33658, 23086, 27211, 27211, 33679,
  /* 13890 */ 27211, 30756, 24012, 24401, 24401, 33716, 24401, 26854, 27480, 18888, 33752, 27855, 33259, 34701, 27211,
  /* 13905 */ 17590, 32102, 24782, 23807, 24401, 18887, 18888, 18888, 27211, 27211, 27212, 33773, 36105, 19868, 25659,
  /* 13920 */ 18888, 23368, 27211, 29157, 19719, 23889, 34454, 29286, 18890, 33794, 25302, 33816, 19447, 34079, 33853,
  /* 13935 */ 31862, 31017, 27856, 31741, 33877, 28920, 33937, 19837, 30461, 34002, 22276, 36041, 34029, 22105, 19419,
  /* 13950 */ 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13965 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13980 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 13995 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14010 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14025 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14040 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14055 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14070 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22833, 18836, 34064, 32616, 34113,
  /* 14085 */ 34141, 34157, 34192, 34208, 32216, 36013, 31549, 31952, 34224, 34248, 34287, 29330, 34350, 34389, 34413,
  /* 14100 */ 34481, 26793, 18866, 26187, 29635, 22293, 18888, 36654, 25783, 34522, 34544, 34566, 25821, 35072, 22164,
  /* 14115 */ 34586, 34609, 34632, 19604, 24036, 36644, 36674, 24681, 18888, 32401, 34654, 31339, 34682, 34698, 27211,
  /* 14130 */ 34717, 34753, 28053, 34812, 34836, 24401, 33619, 19628, 34858, 32236, 34906, 24598, 33523, 27612, 34890,
  /* 14145 */ 34922, 24732, 29246, 36717, 33634, 34465, 32984, 34168, 26750, 34957, 18888, 18888, 34994, 35010, 27211,
  /* 14160 */ 33040, 17590, 29913, 35035, 24401, 36304, 25482, 30171, 35883, 35068, 35088, 26627, 20441, 31173, 35123,
  /* 14175 */ 35143, 35176, 24640, 30492, 29358, 19719, 35192, 35219, 25384, 28801, 35255, 35279, 32586, 34496, 23086,
  /* 14190 */ 23330, 29061, 31017, 27856, 31741, 19840, 25783, 31738, 24547, 25164, 35315, 31796, 35353, 34316, 22105,
  /* 14205 */ 19419, 27963, 24091, 28630, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14220 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14235 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14250 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14265 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14280 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14295 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14310 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14325 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22848, 18836, 22059, 34782,
  /* 14340 */ 34088, 35389, 21008, 35405, 35421, 35454, 18888, 18888, 23466, 35487, 27211, 27211, 27211, 35513, 31154,
  /* 14355 */ 24401, 24401, 24401, 35560, 18888, 26863, 36664, 35601, 24872, 25783, 30389, 23536, 26250, 35647, 35666,
  /* 14370 */ 22164, 19522, 19564, 30582, 35682, 27697, 35575, 29114, 18888, 18888, 18888, 18890, 27211, 35702, 27211,
  /* 14385 */ 27211, 27211, 35723, 24401, 35527, 24401, 24401, 24401, 19628, 30184, 18888, 18888, 18888, 23086, 35739,
  /* 14400 */ 27211, 27211, 27211, 29139, 22938, 24401, 24401, 24401, 24401, 23898, 35756, 18888, 18888, 25025, 35778,
  /* 14415 */ 27211, 27211, 17590, 20064, 35795, 24401, 24401, 18887, 18888, 18888, 27211, 27211, 27212, 24016, 24402,
  /* 14430 */ 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 23917, 18890, 34550, 31833, 22262, 19447,
  /* 14445 */ 23086, 23330, 26418, 31017, 27856, 31741, 19840, 25783, 35812, 19837, 27187, 35841, 33135, 23516, 31008,
  /* 14460 */ 22105, 22148, 28712, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14475 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14490 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14505 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14520 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14535 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14550 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14565 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14580 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22863, 18836, 22059,
  /* 14595 */ 35877, 28723, 34097, 31164, 29183, 22087, 26758, 18888, 22592, 18890, 23989, 27211, 29812, 27211, 22121,
  /* 14610 */ 33778, 24401, 31421, 24401, 18866, 18888, 18888, 26872, 18888, 18888, 25783, 27211, 30732, 27211, 27211,
  /* 14625 */ 35072, 22164, 24401, 24908, 24401, 24401, 24036, 31693, 18888, 18888, 18888, 18888, 18890, 27211, 27211,
  /* 14640 */ 27211, 27211, 27211, 19484, 24401, 24401, 24401, 24401, 24401, 19628, 18888, 18888, 18888, 18888, 23086,
  /* 14655 */ 27211, 27211, 27211, 27211, 30756, 24012, 24401, 24401, 24401, 24401, 26750, 18888, 18888, 18888, 27855,
  /* 14670 */ 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211, 27212, 24016,
  /* 14685 */ 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890, 27211, 31833, 19406,
  /* 14700 */ 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760, 31015, 23516,
  /* 14715 */ 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14730 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14745 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14760 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14775 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14790 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14805 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14820 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14835 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22878, 18836,
  /* 14850 */ 22059, 27837, 27857, 35899, 24401, 35915, 22087, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211,
  /* 14865 */ 22121, 24401, 24401, 24401, 24401, 18866, 18888, 18888, 18888, 18888, 18888, 25783, 27211, 27211, 27211,
  /* 14880 */ 27211, 35072, 22164, 24401, 24401, 24401, 24401, 24036, 31602, 18888, 18888, 18888, 18888, 26223, 27211,
  /* 14895 */ 27211, 27211, 27211, 27211, 19484, 35931, 24401, 24401, 24401, 24401, 19628, 18888, 28136, 18888, 18888,
  /* 14910 */ 35949, 27211, 32862, 27211, 32697, 30756, 24012, 24401, 32283, 24401, 32128, 26750, 18888, 18888, 18888,
  /* 14925 */ 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211, 27212,
  /* 14940 */ 24016, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890, 27211, 31833,
  /* 14955 */ 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760, 31015,
  /* 14970 */ 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 14985 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15000 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15015 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15030 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15045 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15060 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15075 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15090 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 22893,
  /* 15105 */ 18836, 22059, 35974, 34882, 34097, 33960, 29183, 35996, 18888, 23311, 18888, 36029, 27211, 27211, 36064,
  /* 15120 */ 36081, 22121, 24401, 24401, 36104, 33950, 18866, 18888, 18888, 18888, 18888, 18888, 25783, 27211, 27211,
  /* 15135 */ 27211, 27211, 35072, 22164, 24401, 24401, 24401, 24401, 24036, 36121, 18888, 25559, 18888, 18888, 18890,
  /* 15150 */ 27211, 27211, 30313, 27211, 27211, 36154, 24401, 24401, 34397, 24401, 24401, 19628, 28250, 18888, 18888,
  /* 15165 */ 18888, 23086, 30926, 27211, 27211, 27211, 26983, 24012, 33642, 24401, 24401, 24401, 26750, 18888, 18888,
  /* 15180 */ 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 18887, 18888, 18888, 27211, 27211,
  /* 15195 */ 27212, 24016, 24402, 19868, 25659, 18888, 18889, 27211, 27211, 19719, 23889, 19868, 31018, 18890, 27211,
  /* 15210 */ 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782, 19760,
  /* 15225 */ 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15240 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15255 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15270 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15285 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15300 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15315 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15330 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15345 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15360 */ 22339, 18836, 22059, 19354, 27857, 36190, 24401, 36206, 22087, 18888, 18888, 18888, 18007, 27211, 27211,
  /* 15375 */ 27211, 24724, 22121, 24401, 24401, 24401, 30827, 18866, 18888, 36222, 18888, 28795, 18888, 25783, 35100,
  /* 15390 */ 27211, 27429, 27211, 35072, 22164, 30836, 24401, 24499, 24401, 24036, 31693, 18888, 36244, 18888, 18888,
  /* 15405 */ 18890, 27211, 36088, 27211, 27211, 27211, 19484, 24401, 28036, 24401, 24401, 24401, 19628, 18888, 18888,
  /* 15420 */ 35631, 18888, 35762, 27211, 27211, 36277, 27211, 34730, 24012, 24401, 24401, 36300, 24401, 36320, 18888,
  /* 15435 */ 18888, 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401, 24401, 25712, 18888, 18888, 36346,
  /* 15450 */ 27211, 27212, 19184, 24402, 19868, 25659, 32029, 18889, 27211, 33359, 19719, 23889, 36369, 31018, 18890,
  /* 15465 */ 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741, 19840, 25783, 31738, 19837, 25782,
  /* 15480 */ 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15495 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15510 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15525 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15540 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15555 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15570 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15585 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15600 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15615 */ 17590, 22384, 18836, 36389, 19008, 19233, 20367, 36434, 17173, 17595, 36437, 17330, 17349, 18921, 17189,
  /* 15630 */ 17208, 17281, 20355, 36453, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665, 19006, 17265, 22033,
  /* 15645 */ 20765, 17421, 20535, 17192, 20362, 21726, 17311, 18658, 18999, 19008, 17447, 32952, 17497, 17520, 17251,
  /* 15660 */ 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418, 21915, 21940,
  /* 15675 */ 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223, 36531,
  /* 15690 */ 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864, 18731, 17918, 36551,
  /* 15705 */ 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143, 18706, 18052, 18209,
  /* 15720 */ 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392, 17816,
  /* 15735 */ 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590, 17590, 17590, 17590,
  /* 15750 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15765 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15780 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15795 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15810 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15825 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15840 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15855 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 15870 */ 17590, 17590, 22369, 18836, 18987, 19008, 19233, 20367, 19008, 21737, 30763, 36437, 17330, 17349, 18921,
  /* 15885 */ 17189, 17208, 17281, 20355, 17949, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665, 19006, 17265,
  /* 15900 */ 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 32952, 17497, 17520,
  /* 15915 */ 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418, 21915,
  /* 15930 */ 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473, 18223,
  /* 15945 */ 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864, 18731, 17918,
  /* 15960 */ 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143, 18706, 18052,
  /* 15975 */ 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642, 18392,
  /* 15990 */ 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590, 17590, 17590,
  /* 16005 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16020 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16035 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16050 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16065 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16080 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16095 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16110 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16125 */ 17590, 17590, 17590, 21813, 18836, 36489, 19008, 19233, 20367, 19008, 17173, 17737, 36437, 17330, 17349,
  /* 16140 */ 18921, 17189, 17208, 17281, 20355, 17768, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665, 19006,
  /* 16155 */ 17265, 22033, 20765, 17421, 20535, 17192, 20543, 22022, 17311, 18658, 18999, 19008, 17447, 32952, 17497,
  /* 16170 */ 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258, 36418,
  /* 16185 */ 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617, 36473,
  /* 16200 */ 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864, 18731,
  /* 16215 */ 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143, 18706,
  /* 16230 */ 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163, 30642,
  /* 16245 */ 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590, 17590,
  /* 16260 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16275 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16290 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16305 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16320 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16335 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16350 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16365 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16380 */ 17590, 17590, 17590, 17590, 21828, 18836, 18987, 19008, 19233, 20367, 19008, 17173, 30763, 36437, 17330,
  /* 16395 */ 17349, 18921, 17189, 17208, 17281, 20355, 36517, 17308, 17327, 17346, 18918, 18452, 21880, 18649, 18665,
  /* 16410 */ 19006, 17265, 22033, 20765, 17421, 20535, 17192, 18127, 21873, 17311, 18658, 18999, 19008, 17447, 32952,
  /* 16425 */ 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504, 17527, 17258,
  /* 16440 */ 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737, 21946, 17617,
  /* 16455 */ 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481, 19156, 17864,
  /* 16470 */ 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072, 18117, 18143,
  /* 16485 */ 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232, 17796, 17163,
  /* 16500 */ 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535, 17590, 17590,
  /* 16515 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16530 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16545 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16560 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16575 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16590 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16605 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16620 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16635 */ 17590, 17590, 17590, 17590, 17590, 21828, 18836, 19307, 18888, 27857, 30756, 24401, 29183, 28015, 18888,
  /* 16650 */ 18888, 18888, 18890, 27211, 27211, 27211, 27211, 36567, 24401, 24401, 24401, 24401, 22953, 18888, 18888,
  /* 16665 */ 18888, 18888, 18888, 25783, 27211, 27211, 27211, 27211, 28537, 36603, 24401, 24401, 24401, 24401, 24036,
  /* 16680 */ 18881, 18888, 18888, 18888, 18888, 18890, 27211, 27211, 27211, 27211, 27211, 19484, 24401, 24401, 24401,
  /* 16695 */ 24401, 24401, 19628, 18888, 18888, 18888, 18888, 23086, 27211, 27211, 27211, 27211, 30756, 24012, 24401,
  /* 16710 */ 24401, 24401, 24401, 26750, 18888, 18888, 18888, 27855, 27211, 27211, 27211, 17590, 24017, 24401, 24401,
  /* 16725 */ 24401, 18887, 18888, 18888, 27211, 27211, 27212, 24016, 24402, 19868, 25659, 18888, 18889, 27211, 27211,
  /* 16740 */ 19719, 23889, 19868, 31018, 18890, 27211, 31833, 19406, 19447, 23086, 23330, 19828, 31017, 27856, 31741,
  /* 16755 */ 19840, 25783, 31738, 19837, 25782, 19760, 31015, 23516, 31008, 22105, 19419, 27963, 19659, 27951, 17590,
  /* 16770 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16785 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16800 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16815 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16830 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16845 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16860 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16875 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 16890 */ 17590, 17590, 17590, 17590, 17590, 17590, 36629, 36690, 18720, 19008, 19233, 20367, 19008, 17454, 17595,
  /* 16905 */ 36437, 17330, 17349, 18921, 17189, 17208, 17281, 20355, 17223, 17308, 17327, 17346, 18918, 36754, 21880,
  /* 16920 */ 18649, 18665, 19006, 17265, 22033, 20765, 17421, 20535, 17192, 20362, 21726, 17311, 18658, 18999, 19008,
  /* 16935 */ 17447, 32952, 17497, 17520, 17251, 36411, 17782, 20682, 17714, 18326, 17543, 17559, 17585, 21887, 17504,
  /* 16950 */ 17527, 17258, 36418, 21915, 21940, 17611, 36467, 18217, 17633, 17661, 21190, 17703, 21176, 17730, 34737,
  /* 16965 */ 21946, 17617, 36473, 18223, 36531, 17477, 19152, 17860, 17892, 17675, 17753, 17832, 17590, 21620, 17481,
  /* 16980 */ 19156, 17864, 18731, 17918, 36551, 17292, 17934, 17979, 18727, 18681, 18405, 18621, 18039, 18056, 18072,
  /* 16995 */ 18117, 18143, 18706, 18052, 18209, 18250, 18239, 18266, 17963, 18296, 18312, 18376, 17807, 36403, 19232,
  /* 17010 */ 17796, 17163, 30642, 18392, 17816, 32961, 17645, 18805, 18421, 18437, 18519, 17393, 18747, 18505, 18535,
  /* 17025 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 17040 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 17055 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 17070 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 17085 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 17100 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 17115 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 17130 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590, 17590,
  /* 17145 */ 17590, 17590, 17590, 17590, 17590, 17590, 17590, 0, 94242, 0, 118820, 0, 2211840, 102439, 0, 0, 106538,
  /* 17162 */ 98347, 0, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2482176, 2158592,
  /* 17174 */ 2158592, 2158592, 2158592, 2158592, 2158592, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 2207744, 2404352,
  /* 17191 */ 2412544, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 17202 */ 2207744, 2207744, 2207744, 2207744, 2207744, 3104768, 2605056, 2207744, 2207744, 2207744, 2207744,
  /* 17213 */ 2207744, 2207744, 2678784, 2207744, 2695168, 2207744, 2703360, 2207744, 2711552, 2752512, 2207744, 0, 0,
  /* 17226 */ 0, 0, 0, 0, 2166784, 0, 0, 0, 0, 0, 0, 2158592, 2158592, 3170304, 3174400, 2158592, 0, 139, 0, 2158592,
  /* 17246 */ 2158592, 2158592, 2158592, 2158592, 2424832, 2158592, 2158592, 2158592, 2748416, 2756608, 2777088,
  /* 17257 */ 2801664, 2158592, 2158592, 2158592, 2863104, 2891776, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 17268 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 3104768, 2158592, 2158592, 2158592, 2158592,
  /* 17279 */ 2158592, 2158592, 2207744, 2785280, 2207744, 2809856, 2207744, 2207744, 2842624, 2207744, 2207744,
  /* 17290 */ 2207744, 2899968, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2473984,
  /* 17301 */ 2207744, 2207744, 2494464, 2207744, 2207744, 2207744, 2523136, 2158592, 2404352, 2412544, 2158592,
  /* 17312 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 17323 */ 2158592, 2564096, 2158592, 2158592, 2605056, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 17334 */ 2678784, 2158592, 2695168, 2158592, 2703360, 2158592, 2711552, 2752512, 2158592, 2158592, 2785280,
  /* 17345 */ 2158592, 2158592, 2785280, 2158592, 2809856, 2158592, 2158592, 2842624, 2158592, 2158592, 2158592,
  /* 17356 */ 2899968, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 18, 0, 0, 0, 0,
  /* 17371 */ 0, 0, 0, 2211840, 0, 0, 641, 0, 2158592, 0, 0, 0, 0, 0, 0, 0, 0, 2211840, 0, 0, 32768, 0, 2158592, 0,
  /* 17395 */ 2158592, 2158592, 2158592, 2383872, 2158592, 2158592, 2158592, 2158592, 3006464, 2383872, 2207744,
  /* 17406 */ 2207744, 2207744, 2207744, 2158877, 2158877, 2158877, 2158877, 0, 0, 0, 2158877, 2572573, 2158877,
  /* 17419 */ 2158877, 0, 2207744, 2207744, 2596864, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2641920,
  /* 17431 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 0, 0, 0, 167936, 0, 0, 2162688, 0, 0,
  /* 17447 */ 3104768, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 17458 */ 2158592, 2158592, 0, 0, 0, 2146304, 2146304, 2224128, 2224128, 2232320, 2232320, 2232320, 641, 0, 0, 0, 0,
  /* 17475 */ 0, 0, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2531328, 2158592,
  /* 17488 */ 2158592, 2158592, 2158592, 2158592, 2617344, 2158592, 2158592, 2158592, 2158592, 2441216, 2445312,
  /* 17499 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2502656, 2158592, 2158592, 2158592, 2158592,
  /* 17510 */ 2158592, 2158592, 2158592, 2158592, 2580480, 2158592, 2158592, 2158592, 2158592, 2621440, 2158592,
  /* 17521 */ 2580480, 2158592, 2158592, 2158592, 2158592, 2621440, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 17532 */ 2158592, 2699264, 2158592, 2158592, 2158592, 2158592, 2158592, 2748416, 2756608, 2777088, 2801664,
  /* 17543 */ 2207744, 2863104, 2891776, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 17554 */ 2207744, 2207744, 2207744, 2207744, 3018752, 2207744, 3043328, 2207744, 2207744, 2207744, 2207744,
  /* 17565 */ 3080192, 2207744, 2207744, 3112960, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 0, 0,
  /* 17578 */ 0, 172310, 279, 0, 2162688, 0, 0, 2207744, 2207744, 2207744, 3186688, 2207744, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 17599 */ 0, 0, 0, 0, 0, 0, 0, 2158592, 2158592, 2158592, 2404352, 2412544, 2158592, 2510848, 2158592, 2158592,
  /* 17615 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2584576, 2158592, 2609152, 2158592, 2158592, 2629632,
  /* 17626 */ 2158592, 2158592, 2158592, 2686976, 2158592, 2715648, 2158592, 2158592, 3121152, 2158592, 2158592,
  /* 17637 */ 2158592, 3149824, 2158592, 2158592, 3170304, 3174400, 2158592, 2367488, 2207744, 2207744, 2207744,
  /* 17648 */ 2207744, 2158592, 2158592, 2158592, 2158592, 0, 0, 0, 2158592, 2572288, 2158592, 2158592, 0, 2207744,
  /* 17662 */ 2207744, 2207744, 2433024, 2207744, 2453504, 2461696, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 17673 */ 2207744, 2510848, 2207744, 2207744, 2207744, 2207744, 2207744, 2531328, 2207744, 2207744, 2207744,
  /* 17684 */ 2207744, 2207744, 2617344, 2207744, 2207744, 2207744, 2207744, 2158592, 2158592, 2158592, 2158592, 0, 0,
  /* 17697 */ 0, 2158592, 2572288, 2158592, 2158592, 1508, 2715648, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 17709 */ 2207744, 2207744, 2867200, 2207744, 2904064, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 17720 */ 2207744, 2207744, 2580480, 2207744, 2207744, 2207744, 2207744, 2621440, 2207744, 2207744, 2207744,
  /* 17731 */ 3149824, 2207744, 2207744, 3170304, 3174400, 2207744, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 138, 2158592, 2158592,
  /* 17750 */ 2158592, 2404352, 2412544, 2707456, 2732032, 2207744, 2207744, 2207744, 2822144, 2826240, 2207744,
  /* 17761 */ 2895872, 2207744, 2207744, 2924544, 2207744, 2207744, 2973696, 2207744, 0, 0, 0, 0, 0, 0, 2166784, 0, 0,
  /* 17778 */ 0, 0, 0, 285, 2158592, 2158592, 3112960, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 17792 */ 2158592, 2158592, 3186688, 2158592, 2207744, 2207744, 2158592, 2158592, 2158592, 2158592, 2158592, 0, 0,
  /* 17805 */ 0, 2158592, 2158592, 2158592, 2158592, 0, 0, 2535424, 2543616, 2158592, 2158592, 2158592, 0, 0, 0,
  /* 17820 */ 2158592, 2158592, 2158592, 2990080, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 17831 */ 2572288, 2981888, 2207744, 2207744, 3002368, 2207744, 3047424, 3063808, 3076096, 2207744, 2207744,
  /* 17842 */ 2207744, 2207744, 2207744, 2207744, 2207744, 3203072, 2708960, 2732032, 2158592, 2158592, 2158592,
  /* 17853 */ 2822144, 2827748, 2158592, 2895872, 2158592, 2158592, 2924544, 2158592, 2158592, 2973696, 2158592,
  /* 17864 */ 2981888, 2158592, 2158592, 3002368, 2158592, 3047424, 3063808, 3076096, 2158592, 2158592, 2158592,
  /* 17875 */ 2158592, 2158592, 2158592, 2158592, 3203072, 2981888, 2158592, 2158592, 3003876, 2158592, 3047424,
  /* 17886 */ 3063808, 3076096, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 3203072, 2207744,
  /* 17897 */ 2207744, 2207744, 2207744, 2207744, 2424832, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 17908 */ 2207744, 20480, 0, 0, 0, 0, 0, 2162688, 20480, 0, 2523136, 2527232, 2158592, 2158592, 2576384, 2158592,
  /* 17924 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2908160, 2527232,
  /* 17935 */ 2207744, 2207744, 2576384, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 17946 */ 2207744, 2207744, 2908160, 2207744, 0, 0, 0, 0, 0, 0, 2166784, 0, 0, 0, 0, 0, 286, 2158592, 2158592, 0, 0,
  /* 17967 */ 2158592, 2158592, 2158592, 2158592, 2633728, 2658304, 0, 0, 2740224, 2744320, 0, 2834432, 2207744,
  /* 17980 */ 2207744, 2977792, 2207744, 2207744, 2207744, 2207744, 3039232, 2207744, 2207744, 2207744, 2207744,
  /* 17991 */ 2207744, 2207744, 3158016, 0, 0, 29315, 0, 0, 0, 0, 45, 45, 45, 45, 45, 933, 45, 45, 45, 45, 442, 45, 45,
  /* 18014 */ 45, 45, 45, 45, 45, 45, 45, 67, 67, 2494464, 2158592, 2158592, 2158592, 2524757, 2527232, 2158592,
  /* 18030 */ 2158592, 2576384, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 1504, 2158592, 2498560, 2158592,
  /* 18042 */ 2158592, 2158592, 2158592, 2568192, 2158592, 2592768, 2625536, 2158592, 2158592, 2674688, 2736128,
  /* 18053 */ 2158592, 2158592, 0, 2158592, 2912256, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 18065 */ 3108864, 2158592, 2158592, 3133440, 3145728, 3153920, 2375680, 2379776, 2207744, 2207744, 2420736,
  /* 18076 */ 2207744, 2449408, 2207744, 2207744, 2207744, 2498560, 2207744, 2207744, 2207744, 2207744, 2568192,
  /* 18087 */ 2207744, 0, 0, 0, 0, 0, 0, 2166784, 0, 0, 0, 0, 0, 551, 2158592, 2158592, 2158592, 2158592, 2207744,
  /* 18106 */ 2506752, 2207744, 2207744, 2207744, 2207744, 2207744, 2158592, 2506752, 0, 2020, 2158592, 2592768,
  /* 18118 */ 2625536, 2207744, 2207744, 2674688, 2736128, 2207744, 2207744, 2207744, 2912256, 2207744, 2207744,
  /* 18129 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 0, 542, 0, 544,
  /* 18143 */ 2207744, 3108864, 2207744, 2207744, 3133440, 3145728, 3153920, 2375680, 2379776, 2158592, 2158592,
  /* 18154 */ 2420736, 2158592, 2449408, 2158592, 2158592, 2158592, 2158592, 2158592, 3186688, 2158592, 0, 641, 0, 0, 0,
  /* 18169 */ 0, 0, 0, 2367488, 2158592, 2498560, 2158592, 2158592, 1621, 2158592, 2158592, 2568192, 2158592, 2592768,
  /* 18183 */ 2625536, 2158592, 2158592, 2674688, 0, 0, 0, 0, 0, 1608, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1107, 97,
  /* 18205 */ 97, 1110, 97, 97, 3133440, 3145728, 3153920, 2158592, 2408448, 2416640, 2158592, 2465792, 2158592,
  /* 18218 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 3014656, 2158592, 2158592, 3051520,
  /* 18229 */ 2158592, 2158592, 3100672, 2158592, 2158592, 3121152, 2158592, 2158592, 2158592, 3149824, 2416640,
  /* 18240 */ 2207744, 2465792, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2633728,
  /* 18251 */ 2658304, 2740224, 2744320, 2834432, 2949120, 2158592, 2985984, 2158592, 2998272, 2158592, 2158592,
  /* 18262 */ 2158592, 3129344, 2207744, 2408448, 2949120, 2207744, 2985984, 2207744, 2998272, 2207744, 2207744,
  /* 18273 */ 2207744, 3129344, 2158592, 2408448, 2416640, 2158592, 2465792, 2158592, 2158592, 2158592, 2158592,
  /* 18284 */ 2158592, 3186688, 2158592, 0, 32768, 0, 0, 0, 0, 0, 0, 2367488, 2949120, 2158592, 2985984, 2158592,
  /* 18300 */ 2998272, 2158592, 2158592, 2158592, 3129344, 2158592, 2158592, 2478080, 2158592, 2158592, 2158592,
  /* 18311 */ 2535424, 2543616, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 18322 */ 3117056, 2207744, 2207744, 2478080, 2207744, 2207744, 2207744, 2207744, 2699264, 2207744, 2207744,
  /* 18333 */ 2207744, 2207744, 2207744, 2748416, 2756608, 2777088, 2801664, 2207744, 2207744, 2158877, 2158877,
  /* 18344 */ 2158877, 2158877, 2158877, 0, 0, 0, 2158877, 2158877, 2158877, 2158877, 0, 0, 2535709, 2543901, 2158877,
  /* 18359 */ 2158877, 2158877, 0, 0, 0, 2158877, 2158877, 2158877, 2990365, 2158877, 2158877, 2158730, 2158730,
  /* 18372 */ 2158730, 2158730, 2158730, 2572426, 2207744, 2535424, 2543616, 2207744, 2207744, 2207744, 2207744,
  /* 18383 */ 2207744, 2207744, 2207744, 2207744, 2207744, 3117056, 2158592, 2158592, 2478080, 2207744, 2207744,
  /* 18394 */ 2990080, 2207744, 2207744, 2158592, 2158592, 2482176, 2158592, 2158592, 0, 0, 0, 2158592, 2158592,
  /* 18407 */ 2158592, 0, 2158592, 2908160, 2158592, 2158592, 2158592, 2977792, 2158592, 2158592, 2158592, 2158592,
  /* 18419 */ 3039232, 2158592, 2158592, 3010560, 2207744, 2428928, 2207744, 2514944, 2207744, 2588672, 2207744,
  /* 18430 */ 2838528, 2207744, 2207744, 2207744, 3010560, 2158592, 2428928, 2158592, 2514944, 0, 0, 2158592, 2588672,
  /* 18443 */ 2158592, 0, 2838528, 2158592, 2158592, 2158592, 3010560, 2158592, 2506752, 2158592, 18, 0, 0, 0, 0, 0, 0,
  /* 18460 */ 0, 2211840, 0, 0, 0, 0, 2158592, 0, 0, 29315, 922, 0, 0, 0, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 18485 */ 45, 45, 1539, 45, 3006464, 2383872, 0, 2020, 2158592, 2158592, 2158592, 2158592, 3006464, 2158592,
  /* 18499 */ 2637824, 2953216, 2158592, 2207744, 2637824, 2953216, 2207744, 0, 0, 2158592, 2637824, 2953216, 2158592,
  /* 18512 */ 2539520, 2158592, 2539520, 2207744, 0, 0, 2539520, 2158592, 2158592, 2158592, 2158592, 2207744, 2506752,
  /* 18525 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2158592, 2506752, 0, 0, 2158592, 2207744, 0, 2158592,
  /* 18538 */ 2158592, 2207744, 0, 2158592, 2158592, 2207744, 0, 2158592, 2965504, 2965504, 2965504, 0, 0, 0, 0, 0,
  /* 18554 */ 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2474269, 2158877, 2158877, 0, 0,
  /* 18567 */ 2158877, 2158877, 2158877, 2158877, 2634013, 2658589, 0, 0, 2740509, 2744605, 0, 2834717, 40976, 18,
  /* 18581 */ 36884, 45078, 24, 28, 90143, 94242, 118820, 102439, 106538, 98347, 118820, 118820, 118820, 40976, 18, 18,
  /* 18597 */ 36884, 0, 0, 0, 24, 24, 24, 27, 27, 27, 27, 90143, 0, 0, 86016, 0, 0, 2211840, 102439, 0, 0, 0, 98347, 0,
  /* 18621 */ 2158592, 2158592, 2158592, 2158592, 2158592, 3158016, 0, 2375680, 2379776, 2158592, 2158592, 2420736,
  /* 18633 */ 2158592, 2449408, 2158592, 2158592, 0, 94242, 0, 0, 0, 2211840, 102439, 0, 0, 106538, 98347, 135, 2158592,
  /* 18650 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2564096, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 18661 */ 2596864, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2641920, 2158592, 2158592, 2158592,
  /* 18672 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2781184, 2793472, 2494464, 2158592,
  /* 18683 */ 2158592, 2158592, 2523136, 2527232, 2158592, 2158592, 2576384, 2158592, 2158592, 2158592, 2158592,
  /* 18694 */ 2158592, 2158592, 0, 40976, 0, 18, 18, 24, 0, 27, 27, 0, 2158592, 2498560, 2158592, 2158592, 0, 2158592,
  /* 18712 */ 2158592, 2568192, 2158592, 2592768, 2625536, 2158592, 2158592, 2674688, 0, 0, 0, 0, 0, 2211840, 0, 0, 0,
  /* 18729 */ 0, 0, 0, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2473984, 2158592,
  /* 18742 */ 2158592, 2494464, 2158592, 2158592, 2158592, 3006464, 2383872, 0, 0, 2158592, 2158592, 2158592, 2158592,
  /* 18755 */ 3006464, 2158592, 2637824, 2953216, 2158592, 2207744, 2637824, 2953216, 40976, 18, 36884, 45078, 24, 27,
  /* 18769 */ 147488, 94242, 147456, 147488, 106538, 98347, 0, 0, 147456, 40976, 18, 18, 36884, 0, 45078, 0, 24, 24, 24,
  /* 18788 */ 27, 27, 27, 27, 0, 81920, 0, 94242, 0, 0, 0, 2211840, 0, 0, 0, 106538, 98347, 0, 2158592, 2158592,
  /* 18808 */ 2158592, 2158592, 2158592, 2158592, 2428928, 2158592, 2514944, 2158592, 2588672, 2158592, 2838528,
  /* 18819 */ 2158592, 2158592, 40976, 18, 151573, 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 0,
  /* 18836 */ 40976, 18, 18, 36884, 0, 45078, 0, 24, 24, 24, 27, 27, 27, 27, 90143, 0, 0, 1315, 0, 97, 97, 97, 97, 97,
  /* 18860 */ 97, 97, 97, 97, 97, 1487, 97, 18, 131427, 0, 0, 0, 0, 0, 0, 362, 0, 0, 365, 29315, 367, 0, 0, 29315, 0, 0,
  /* 18886 */ 0, 0, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 130, 94242, 0, 0, 0,
  /* 18911 */ 2211840, 102439, 0, 0, 106538, 98347, 0, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 3096576,
  /* 18925 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2207744,
  /* 18936 */ 2207744, 2158592, 18, 0, 0, 0, 0, 0, 0, 0, 2211840, 0, 0, 0, 0, 2158592, 644, 2207744, 2207744, 2207744,
  /* 18956 */ 3186688, 2207744, 0, 1080, 0, 1084, 0, 1088, 0, 0, 0, 0, 0, 0, 0, 2158730, 2158730, 2158730, 2158730,
  /* 18975 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2531466, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 18986 */ 2617482, 0, 94242, 0, 0, 0, 2211840, 102439, 0, 0, 106538, 98347, 0, 2158592, 2158592, 2158592, 2158592,
  /* 19003 */ 2158592, 2781184, 2793472, 2158592, 2818048, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 19014 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 40976, 18,
  /* 19026 */ 36884, 45078, 24, 27, 90143, 159779, 159744, 102439, 159779, 98347, 0, 0, 159744, 40976, 18, 18, 36884, 0,
  /* 19044 */ 45078, 0, 2224253, 172032, 2224253, 2232448, 2232448, 172032, 2232448, 90143, 0, 0, 2170880, 0, 0, 550,
  /* 19060 */ 829, 2158592, 2158592, 2158592, 2387968, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 0, 40976,
  /* 19073 */ 0, 18, 18, 124, 124, 127, 127, 127, 40976, 18, 36884, 45078, 25, 29, 90143, 94242, 0, 102439, 106538,
  /* 19092 */ 98347, 0, 0, 163931, 40976, 18, 18, 36884, 0, 45078, 249856, 24, 24, 24, 27, 27, 27, 27, 90143, 0, 0,
  /* 19113 */ 2170880, 0, 0, 827, 0, 2158592, 2158592, 2158592, 2387968, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 19127 */ 2158592, 0, 40976, 0, 4243810, 4243810, 24, 24, 27, 27, 27, 2207744, 0, 0, 0, 0, 0, 0, 2166784, 0, 0, 0,
  /* 19149 */ 0, 57344, 286, 2158592, 2158592, 2158592, 2158592, 2707456, 2732032, 2158592, 2158592, 2158592, 2822144,
  /* 19162 */ 2826240, 2158592, 2895872, 2158592, 2158592, 2924544, 2158592, 2158592, 2973696, 2158592, 2207744,
  /* 19173 */ 2207744, 2207744, 3186688, 2207744, 0, 0, 0, 0, 0, 0, 53248, 0, 0, 0, 0, 0, 97, 97, 97, 97, 97, 1613, 97,
  /* 19196 */ 97, 97, 97, 97, 97, 1495, 97, 97, 97, 97, 97, 97, 97, 97, 97, 566, 97, 97, 97, 97, 97, 97, 2207744, 0, 0,
  /* 19221 */ 0, 0, 0, 0, 2166784, 546, 0, 0, 0, 0, 286, 2158592, 2158592, 2158592, 2207744, 2207744, 2207744, 2207744,
  /* 19239 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 17, 18, 36884,
  /* 19252 */ 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 20480, 120, 121, 18, 18, 36884, 0, 45078, 0,
  /* 19272 */ 24, 24, 24, 27, 27, 27, 27, 90143, 0, 0, 2170880, 0, 53248, 550, 0, 2158592, 2158592, 2158592, 2387968,
  /* 19291 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 0, 40976, 196608, 18, 266240, 24, 24, 27, 27, 27, 0,
  /* 19308 */ 94242, 0, 0, 0, 38, 102439, 0, 0, 106538, 98347, 0, 45, 45, 45, 45, 45, 45, 45, 1535, 45, 45, 45, 45, 45,
  /* 19332 */ 45, 45, 1416, 45, 45, 45, 45, 45, 45, 45, 45, 424, 45, 45, 45, 45, 45, 45, 45, 45, 45, 405, 45, 45, 45,
  /* 19357 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 199, 45, 45, 67, 67, 67, 67, 67, 491, 67, 67, 67, 67, 67, 67, 67,
  /* 19383 */ 67, 67, 67, 67, 1766, 67, 67, 67, 1767, 67, 24850, 24850, 12564, 12564, 0, 0, 2166784, 546, 0, 53531,
  /* 19403 */ 53531, 0, 286, 97, 97, 0, 0, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 0, 97, 97, 97, 45, 45, 45, 45, 45, 45,
  /* 19430 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 743, 57889, 0, 2170880, 0, 0, 550, 0, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 19455 */ 97, 45, 45, 45, 45, 45, 45, 45, 45, 1856, 45, 1858, 1859, 67, 67, 67, 1009, 67, 67, 67, 67, 67, 67, 67,
  /* 19479 */ 67, 67, 67, 67, 1021, 67, 67, 67, 67, 67, 25398, 0, 13112, 0, 54074, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2367773,
  /* 19504 */ 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2699549, 2158877, 2158877, 2158877, 2158877,
  /* 19515 */ 2158877, 2748701, 2756893, 2777373, 2801949, 97, 1115, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 19535 */ 97, 857, 97, 67, 67, 67, 67, 67, 1258, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1826, 67, 97, 97, 97,
  /* 19560 */ 97, 97, 97, 1338, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 870, 97, 97, 67, 67, 67, 1463, 67,
  /* 19585 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1579, 67, 67, 97, 97, 97, 1518, 97, 97, 97, 97, 97, 97,
  /* 19610 */ 97, 97, 97, 97, 97, 97, 97, 904, 905, 97, 97, 97, 97, 1620, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0,
  /* 19636 */ 921, 0, 0, 0, 0, 0, 0, 45, 1679, 67, 67, 67, 1682, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1690, 67, 0, 0, 97,
  /* 19663 */ 97, 97, 97, 45, 45, 67, 67, 0, 0, 97, 97, 45, 45, 45, 669, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 19690 */ 189, 45, 45, 45, 1748, 45, 45, 45, 1749, 1750, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 1959, 67,
  /* 19714 */ 67, 67, 67, 1768, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1791, 97, 97, 97,
  /* 19739 */ 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 1802, 67, 1817, 67, 67, 67, 67, 67, 67, 1823, 67, 67, 67, 67,
  /* 19764 */ 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 0, 97, 97, 97, 97, 1848, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 19791 */ 45, 659, 45, 45, 45, 45, 45, 45, 45, 1863, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 495, 67, 67,
  /* 19816 */ 67, 67, 67, 1878, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 0, 0, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97,
  /* 19844 */ 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 97, 97, 97, 97, 0, 0, 0, 1973, 97, 97, 97,
  /* 19871 */ 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1165, 97, 1167, 67, 24850, 24850, 12564, 12564, 0,
  /* 19894 */ 0, 2166784, 0, 0, 53531, 53531, 0, 286, 97, 97, 0, 0, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 1789, 97, 0,
  /* 19919 */ 94242, 0, 0, 0, 2211840, 102439, 0, 0, 106538, 98347, 136, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 19935 */ 3158016, 229376, 2375680, 2379776, 2158592, 2158592, 2420736, 2158592, 2449408, 2158592, 2158592, 67,
  /* 19947 */ 24850, 24850, 12564, 12564, 0, 0, 280, 547, 0, 53531, 53531, 0, 286, 97, 97, 0, 0, 97, 97, 97, 97, 97, 97,
  /* 19970 */ 0, 1788, 97, 97, 0, 97, 2024, 97, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 235, 67, 67, 67,
  /* 19996 */ 67, 67, 57889, 547, 547, 0, 0, 550, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 45, 45, 45, 1799, 45, 45, 45,
  /* 20021 */ 67, 67, 67, 67, 67, 25398, 0, 13112, 0, 54074, 0, 0, 1092, 0, 0, 0, 0, 0, 97, 97, 97, 97, 1612, 97, 97,
  /* 20046 */ 97, 97, 1616, 97, 1297, 1472, 0, 0, 0, 0, 1303, 1474, 0, 0, 0, 0, 1309, 1476, 0, 0, 0, 0, 97, 97, 97,
  /* 20071 */ 1481, 97, 97, 97, 97, 97, 97, 1488, 97, 0, 1474, 0, 1476, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 20096 */ 607, 97, 97, 97, 97, 40976, 18, 36884, 45078, 26, 30, 90143, 94242, 0, 102439, 106538, 98347, 0, 0,
  /* 20115 */ 213080, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 143448, 40976, 18,
  /* 20133 */ 18, 36884, 0, 45078, 0, 24, 24, 24, 27, 27, 27, 27, 0, 0, 0, 0, 97, 97, 97, 97, 1482, 97, 1483, 97, 97,
  /* 20158 */ 97, 97, 97, 97, 1326, 97, 97, 1329, 1330, 97, 97, 97, 97, 97, 97, 1159, 1160, 97, 97, 97, 97, 97, 97, 97,
  /* 20182 */ 97, 590, 97, 97, 97, 97, 97, 97, 97, 0, 94242, 0, 0, 0, 2211974, 102439, 0, 0, 106538, 98347, 0, 2158730,
  /* 20204 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2474122, 2158730, 2158730, 2494602,
  /* 20215 */ 2158730, 2158730, 2158730, 2809994, 2158730, 2158730, 2842762, 2158730, 2158730, 2158730, 2900106,
  /* 20226 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 3014794, 2158730, 2158730,
  /* 20237 */ 3051658, 2158730, 2158730, 3100810, 2158730, 2158730, 2158730, 2158730, 3096714, 2158730, 2158730,
  /* 20248 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2207744, 2207744, 2207744,
  /* 20259 */ 2207744, 2207744, 2572288, 2207744, 2207744, 2207744, 2207744, 541, 541, 543, 543, 0, 0, 2166784, 0, 548,
  /* 20275 */ 549, 549, 0, 286, 2158877, 2158877, 2158877, 2863389, 2892061, 2158877, 2158877, 2158877, 2158877,
  /* 20288 */ 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 3186973, 2158877, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 20305 */ 2367626, 2158877, 2404637, 2412829, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877,
  /* 20316 */ 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2564381, 2158877,
  /* 20327 */ 2158877, 2605341, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2679069, 2158877, 2695453,
  /* 20338 */ 2158877, 2703645, 2158877, 2711837, 2752797, 2158877, 0, 2158877, 2158877, 2158877, 2384010, 2158730,
  /* 20350 */ 2158730, 2158730, 2158730, 3006602, 2383872, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 20361 */ 3096576, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 20372 */ 2207744, 2207744, 0, 0, 0, 0, 0, 0, 2162688, 0, 0, 2158877, 2785565, 2158877, 2810141, 2158877, 2158877,
  /* 20389 */ 2842909, 2158877, 2158877, 2158877, 2900253, 2158877, 2158877, 2158877, 2158877, 2158877, 2531613,
  /* 20400 */ 2158877, 2158877, 2158877, 2158877, 2158877, 2617629, 2158877, 2158877, 2158877, 2158877, 2158730,
  /* 20411 */ 2818186, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20422 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 3105053, 2158877, 2158877, 2158877, 2158877,
  /* 20433 */ 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 0, 0, 0, 0, 0, 97, 97, 97, 1611,
  /* 20450 */ 97, 97, 97, 97, 97, 97, 97, 1496, 97, 97, 1499, 97, 97, 97, 97, 97, 2441354, 2445450, 2158730, 2158730,
  /* 20470 */ 2158730, 2158730, 2158730, 2158730, 2502794, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20481 */ 2158730, 2433162, 2158730, 2453642, 2461834, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20492 */ 2580618, 2158730, 2158730, 2158730, 2158730, 2621578, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20503 */ 2158730, 2699402, 2158730, 2158730, 2158730, 2158730, 2678922, 2158730, 2695306, 2158730, 2703498,
  /* 20514 */ 2158730, 2711690, 2752650, 2158730, 2158730, 2785418, 2158730, 2158730, 2158730, 3113098, 2158730,
  /* 20525 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 3186826, 2158730, 2207744,
  /* 20536 */ 2207744, 2207744, 2207744, 2781184, 2793472, 2207744, 2818048, 2207744, 2207744, 2207744, 2207744,
  /* 20547 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 0, 541, 0, 543, 2158877, 2502941,
  /* 20561 */ 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2580765, 2158877, 2158877,
  /* 20572 */ 2158877, 2158877, 2621725, 2158877, 3019037, 2158877, 3043613, 2158877, 2158877, 2158877, 2158877,
  /* 20583 */ 3080477, 2158877, 2158877, 3113245, 2158877, 2158877, 2158877, 2158877, 0, 2158877, 2908445, 2158877,
  /* 20595 */ 2158877, 2158877, 2978077, 2158877, 2158877, 2158877, 2158877, 3039517, 2158877, 2158730, 2510986,
  /* 20606 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2584714, 2158730, 2609290, 2158730,
  /* 20617 */ 2158730, 2629770, 2158730, 2158730, 2158730, 2388106, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20628 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2605194, 2158730, 2158730,
  /* 20639 */ 2158730, 2158730, 2687114, 2158730, 2715786, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20650 */ 2158730, 2867338, 2158730, 2904202, 2158730, 2158730, 2158730, 2642058, 2158730, 2158730, 2158730,
  /* 20661 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2781322, 2793610, 2158730, 3121290,
  /* 20672 */ 2158730, 2158730, 2158730, 3149962, 2158730, 2158730, 3170442, 3174538, 2158730, 2367488, 2207744,
  /* 20683 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2441216, 2445312, 2207744, 2207744, 2207744,
  /* 20694 */ 2207744, 2207744, 2207744, 2502656, 2158877, 2433309, 2158877, 2453789, 2461981, 2158877, 2158877,
  /* 20705 */ 2158877, 2158877, 2158877, 2158877, 2511133, 2158877, 2158877, 2158877, 2158877, 2584861, 2158877,
  /* 20716 */ 2609437, 2158877, 2158877, 2629917, 2158877, 2158877, 2158877, 2687261, 2158877, 2715933, 2158877,
  /* 20727 */ 2158730, 2158730, 2973834, 2158730, 2982026, 2158730, 2158730, 3002506, 2158730, 3047562, 3063946,
  /* 20738 */ 3076234, 2158730, 2158730, 2158730, 2158730, 2207744, 2506752, 2207744, 2207744, 2207744, 2207744,
  /* 20749 */ 2207744, 2158877, 2507037, 0, 0, 2158877, 2158730, 2158730, 2158730, 3203210, 2207744, 2207744, 2207744,
  /* 20762 */ 2207744, 2207744, 2424832, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 20773 */ 2207744, 2207744, 2207744, 2207744, 2564096, 2207744, 2207744, 2207744, 2707741, 2732317, 2158877,
  /* 20784 */ 2158877, 2158877, 2822429, 2826525, 2158877, 2896157, 2158877, 2158877, 2924829, 2158877, 2158877,
  /* 20795 */ 2973981, 2158877, 18, 0, 0, 0, 0, 0, 0, 0, 2211840, 0, 0, 642, 0, 2158592, 0, 45, 1529, 45, 45, 45, 45,
  /* 20818 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 1755, 45, 67, 67, 2982173, 2158877, 2158877, 3002653, 2158877,
  /* 20836 */ 3047709, 3064093, 3076381, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 3203357,
  /* 20847 */ 2523274, 2527370, 2158730, 2158730, 2576522, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20858 */ 2158730, 2158730, 2158730, 2158730, 2908298, 2494749, 2158877, 2158877, 2158877, 2523421, 2527517,
  /* 20869 */ 2158877, 2158877, 2576669, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 0, 40976, 0, 18, 18,
  /* 20883 */ 4321280, 2224253, 2232448, 4329472, 2232448, 2158730, 2498698, 2158730, 2158730, 2158730, 2158730,
  /* 20894 */ 2568330, 2158730, 2592906, 2625674, 2158730, 2158730, 2674826, 2736266, 2158730, 2158730, 2158730,
  /* 20905 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 20916 */ 2207744, 2207744, 2207744, 2158730, 2912394, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20927 */ 2158730, 3109002, 2158730, 2158730, 3133578, 3145866, 3154058, 2375680, 2207744, 3108864, 2207744,
  /* 20938 */ 2207744, 3133440, 3145728, 3153920, 2375965, 2380061, 2158877, 2158877, 2421021, 2158877, 2449693,
  /* 20949 */ 2158877, 2158877, 2158877, 3117341, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20960 */ 2158730, 2158730, 2158730, 2158730, 2158730, 3104906, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 20971 */ 2158730, 2158877, 2498845, 2158877, 2158877, 0, 2158877, 2158877, 2568477, 2158877, 2593053, 2625821,
  /* 20983 */ 2158877, 2158877, 2674973, 0, 0, 0, 0, 97, 97, 1480, 97, 97, 97, 97, 97, 1485, 97, 97, 97, 0, 97, 97,
  /* 21005 */ 1729, 97, 1731, 97, 97, 97, 97, 97, 97, 97, 311, 97, 97, 97, 97, 97, 97, 97, 97, 1520, 97, 97, 1523, 97,
  /* 21029 */ 97, 1526, 97, 2736413, 2158877, 2158877, 0, 2158877, 2912541, 2158877, 2158877, 2158877, 2158877, 2158877,
  /* 21043 */ 2158877, 2158877, 3109149, 2158877, 2158877, 3014941, 2158877, 2158877, 3051805, 2158877, 2158877,
  /* 21054 */ 3100957, 2158877, 2158877, 3121437, 2158877, 2158877, 2158877, 3150109, 3133725, 3146013, 3154205,
  /* 21065 */ 2158730, 2408586, 2416778, 2158730, 2465930, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730,
  /* 21076 */ 2158730, 2158730, 3018890, 2158730, 3043466, 2158730, 2158730, 2158730, 2158730, 3080330, 2633866,
  /* 21087 */ 2658442, 2740362, 2744458, 2834570, 2949258, 2158730, 2986122, 2158730, 2998410, 2158730, 2158730,
  /* 21098 */ 2158730, 3129482, 2207744, 2408448, 2949120, 2207744, 2985984, 2207744, 2998272, 2207744, 2207744,
  /* 21109 */ 2207744, 3129344, 2158877, 2408733, 2416925, 2158877, 2466077, 2158877, 2158877, 3170589, 3174685,
  /* 21120 */ 2158877, 0, 0, 0, 2158730, 2158730, 2158730, 2158730, 2158730, 2424970, 2158730, 2158730, 2158730,
  /* 21133 */ 2158730, 2707594, 2732170, 2158730, 2158730, 2158730, 2822282, 2826378, 2158730, 2896010, 2158730,
  /* 21144 */ 2158730, 2924682, 2949405, 2158877, 2986269, 2158877, 2998557, 2158877, 2158877, 2158877, 3129629,
  /* 21155 */ 2158730, 2158730, 2478218, 2158730, 2158730, 2158730, 2535562, 2543754, 2158730, 2158730, 2158730,
  /* 21166 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 3117194, 2207744, 2207744, 2478080, 2207744,
  /* 21177 */ 2207744, 2207744, 2207744, 3014656, 2207744, 2207744, 3051520, 2207744, 2207744, 3100672, 2207744,
  /* 21188 */ 2207744, 3121152, 2207744, 2207744, 2207744, 2207744, 2207744, 2584576, 2207744, 2609152, 2207744,
  /* 21199 */ 2207744, 2629632, 2207744, 2207744, 2207744, 2686976, 2207744, 2207744, 2535424, 2543616, 2207744,
  /* 21210 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 3117056, 2158877, 2158877,
  /* 21221 */ 2478365, 0, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158730, 2158730, 2482314, 2158730,
  /* 21233 */ 2158730, 2158730, 2158730, 2158730, 2158730, 2207744, 2207744, 2207744, 2387968, 2207744, 2207744,
  /* 21244 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 0, 823, 0, 825,
  /* 21258 */ 2158730, 2158730, 2158730, 2990218, 2158730, 2158730, 2207744, 2207744, 2482176, 2207744, 2207744,
  /* 21269 */ 2207744, 2207744, 2207744, 2207744, 2207744, 0, 0, 0, 0, 0, 0, 2162688, 135, 0, 2207744, 2207744, 2990080,
  /* 21286 */ 2207744, 2207744, 2158877, 2158877, 2482461, 2158877, 2158877, 0, 0, 0, 2158877, 2158877, 2158877,
  /* 21299 */ 2158877, 2158877, 2158730, 2429066, 2158730, 2515082, 2158730, 2588810, 2158730, 2838666, 2158730,
  /* 21310 */ 2158730, 2158730, 3010698, 2207744, 2428928, 2207744, 2514944, 2207744, 2588672, 2207744, 2838528,
  /* 21321 */ 2207744, 2207744, 2207744, 3010560, 2158877, 2429213, 2158877, 2515229, 0, 0, 2158877, 2588957, 2158877,
  /* 21334 */ 0, 2838813, 2158877, 2158877, 2158877, 3010845, 2158730, 2506890, 2158730, 2158730, 2158730, 2748554,
  /* 21346 */ 2756746, 2777226, 2801802, 2158730, 2158730, 2158730, 2863242, 2891914, 2158730, 2158730, 2158730,
  /* 21357 */ 2158730, 2158730, 2158730, 2564234, 2158730, 2158730, 2158730, 2158730, 2158730, 2597002, 2158730,
  /* 21368 */ 2158730, 2158730, 3006464, 2384157, 0, 0, 2158877, 2158877, 2158877, 2158877, 3006749, 2158730, 2637962,
  /* 21381 */ 2953354, 2158730, 2207744, 2637824, 2953216, 2207744, 0, 0, 2158877, 2638109, 2953501, 2158877, 2539658,
  /* 21394 */ 2158730, 2539520, 2207744, 0, 0, 2539805, 2158877, 2158730, 2158730, 2158730, 2977930, 2158730, 2158730,
  /* 21407 */ 2158730, 2158730, 3039370, 2158730, 2158730, 2158730, 2158730, 2158730, 2158730, 3158154, 2207744, 0,
  /* 21419 */ 2158877, 2158730, 2207744, 0, 2158877, 2158730, 2207744, 0, 2158877, 2965642, 2965504, 2965789, 0, 0, 0,
  /* 21434 */ 0, 1315, 0, 0, 0, 0, 97, 97, 97, 97, 97, 97, 97, 1484, 97, 97, 97, 97, 2158592, 18, 0, 122880, 0, 0, 0,
  /* 21459 */ 77824, 0, 2211840, 0, 0, 0, 0, 2158592, 0, 356, 0, 0, 0, 0, 0, 0, 28809, 0, 139, 45, 45, 45, 45, 45, 45,
  /* 21484 */ 1751, 45, 45, 45, 45, 45, 45, 45, 67, 67, 1427, 67, 67, 67, 67, 67, 1432, 67, 67, 67, 3104768, 2158592,
  /* 21506 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 122880,
  /* 21518 */ 0, 0, 0, 0, 1315, 0, 0, 0, 0, 97, 97, 97, 97, 97, 97, 1322, 550, 0, 286, 0, 2158592, 2158592, 2158592,
  /* 21541 */ 2158592, 2158592, 2424832, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 0, 40976, 0, 18, 18, 24,
  /* 21556 */ 24, 4329472, 27, 27, 2207744, 2207744, 2977792, 2207744, 2207744, 2207744, 2207744, 3039232, 2207744,
  /* 21569 */ 2207744, 2207744, 2207744, 2207744, 2207744, 3158016, 542, 0, 0, 0, 542, 0, 544, 0, 0, 0, 544, 0, 550, 0,
  /* 21589 */ 0, 0, 0, 0, 97, 97, 1610, 97, 97, 97, 97, 97, 97, 97, 97, 898, 97, 97, 97, 97, 97, 97, 97, 0, 94242, 0, 0,
  /* 21616 */ 0, 2211840, 0, 0, 0, 0, 0, 0, 2158592, 2158592, 2158592, 2158592, 2158592, 2424832, 2158592, 2158592,
  /* 21632 */ 2158592, 2158592, 2158592, 2158592, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 237568, 102439, 106538,
  /* 21647 */ 98347, 0, 0, 20480, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 192512,
  /* 21666 */ 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 94, 40976, 18, 36884,
  /* 21684 */ 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 96, 40976, 18, 36884, 45078, 24, 27, 90143,
  /* 21703 */ 94242, 0, 102439, 106538, 98347, 0, 0, 12378, 40976, 18, 18, 36884, 0, 45078, 0, 24, 24, 24, 126, 126,
  /* 21723 */ 126, 126, 90143, 0, 0, 2170880, 0, 0, 0, 0, 2158592, 2158592, 2158592, 2387968, 2158592, 2158592, 2158592,
  /* 21740 */ 2158592, 2158592, 2158592, 20480, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 40976, 18, 36884, 45078, 24, 27,
  /* 21759 */ 90143, 94242, 241664, 102439, 106538, 98347, 0, 0, 20568, 40976, 18, 36884, 45078, 24, 27, 90143, 94242,
  /* 21776 */ 0, 102439, 106538, 98347, 0, 0, 200797, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0, 102439, 106538,
  /* 21794 */ 98347, 0, 0, 20480, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0, 0, 0, 44, 0, 0, 20575, 40976, 18,
  /* 21815 */ 36884, 45078, 24, 27, 90143, 94242, 0, 41, 41, 41, 0, 0, 1126400, 40976, 18, 36884, 45078, 24, 27, 90143,
  /* 21835 */ 94242, 0, 102439, 106538, 98347, 0, 0, 0, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0, 102439,
  /* 21853 */ 106538, 98347, 0, 0, 89, 40976, 18, 18, 36884, 0, 45078, 0, 24, 24, 24, 27, 131201, 27, 27, 90143, 0, 0,
  /* 21875 */ 2170880, 0, 0, 550, 0, 2158592, 2158592, 2158592, 2387968, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 21889 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2441216, 2445312, 2158592, 2158592,
  /* 21900 */ 2158592, 2158592, 2158592, 0, 94242, 0, 0, 208896, 2211840, 102439, 0, 0, 106538, 98347, 0, 2158592,
  /* 21916 */ 2158592, 2158592, 2158592, 2158592, 3186688, 2158592, 0, 0, 0, 0, 0, 0, 0, 0, 2367488, 32768, 0, 0, 0, 0,
  /* 21936 */ 0, 0, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2433024, 2158592,
  /* 21949 */ 2453504, 2461696, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2510848, 2158592, 2158592,
  /* 21960 */ 2158592, 2158592, 40976, 18, 36884, 245783, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 20480,
  /* 21977 */ 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 221184, 40976, 18, 36884,
  /* 21995 */ 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 180224, 40976, 18, 18, 36884, 155648, 45078,
  /* 22013 */ 0, 24, 24, 217088, 27, 27, 27, 217088, 90143, 0, 0, 2170880, 0, 0, 828, 0, 2158592, 2158592, 2158592,
  /* 22032 */ 2387968, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2207744, 2207744, 2207744, 2387968,
  /* 22043 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744, 0, 0, 0, 0, 0, 0, 2162688, 233472, 0, 0,
  /* 22060 */ 94242, 0, 0, 0, 38, 102439, 0, 0, 106538, 98347, 28809, 45, 45, 45, 45, 45, 718, 45, 45, 45, 45, 45, 45,
  /* 22083 */ 45, 45, 45, 727, 131427, 0, 0, 0, 0, 362, 0, 365, 28809, 367, 139, 45, 45, 45, 45, 45, 45, 1808, 45, 45,
  /* 22107 */ 45, 45, 67, 67, 67, 67, 67, 67, 67, 97, 97, 0, 0, 97, 67, 24850, 24850, 12564, 12564, 0, 57889, 0, 0, 0,
  /* 22131 */ 53531, 53531, 367, 286, 97, 97, 0, 0, 97, 97, 97, 97, 97, 97, 1787, 0, 97, 97, 0, 97, 97, 97, 45, 45, 45,
  /* 22156 */ 45, 2029, 45, 67, 67, 67, 67, 2033, 57889, 0, 0, 54074, 54074, 550, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 22180 */ 45, 1798, 45, 45, 1800, 45, 45, 0, 1472, 0, 0, 0, 0, 0, 1474, 0, 0, 0, 0, 0, 1476, 0, 0, 0, 0, 1315, 0, 0,
  /* 22208 */ 0, 0, 97, 97, 97, 97, 1320, 97, 97, 0, 0, 97, 97, 97, 97, 1786, 97, 0, 0, 97, 97, 0, 1790, 1527, 45, 45,
  /* 22234 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 663, 67, 24850, 24850, 12564, 12564, 0, 57889, 281, 0,
  /* 22257 */ 0, 53531, 53531, 367, 286, 97, 97, 0, 0, 97, 97, 97, 1785, 97, 97, 0, 0, 97, 97, 0, 97, 97, 1979, 97, 97,
  /* 22282 */ 45, 45, 1983, 45, 1984, 45, 45, 45, 45, 45, 652, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 690, 45, 45, 694,
  /* 22307 */ 45, 45, 40976, 19, 36884, 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 262144, 40976, 18,
  /* 22326 */ 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 46, 67, 98, 40976, 18, 36884, 45078, 24,
  /* 22344 */ 27, 90143, 94242, 38, 102439, 106538, 98347, 45, 67, 97, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0,
  /* 22363 */ 102439, 106538, 98347, 0, 0, 258048, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0, 102439, 106538,
  /* 22380 */ 98347, 0, 0, 1122423, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 0, 1114152, 1114152, 1114152, 0, 0,
  /* 22398 */ 1114112, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 37, 102439, 106538, 98347, 0, 0, 204800, 40976,
  /* 22415 */ 18, 36884, 45078, 24, 27, 90143, 94242, 0, 102439, 106538, 98347, 0, 0, 57436, 40976, 18, 36884, 45078,
  /* 22433 */ 24, 27, 33, 33, 0, 33, 33, 33, 0, 0, 0, 40976, 18, 18, 36884, 0, 45078, 0, 124, 124, 124, 127, 127, 127,
  /* 22457 */ 127, 90143, 0, 0, 2170880, 0, 0, 550, 0, 2158877, 2158877, 2158877, 2388253, 2158877, 2158877, 2158877,
  /* 22473 */ 2158877, 2158877, 2781469, 2793757, 2158877, 2818333, 2158877, 2158877, 2158877, 2158877, 2158877,
  /* 22484 */ 2158877, 2158877, 2867485, 2158877, 2904349, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877,
  /* 22495 */ 2158877, 3096861, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877,
  /* 22506 */ 2441501, 2445597, 2158877, 2158877, 2158877, 2158877, 2158877, 40976, 122, 123, 36884, 0, 45078, 0, 24,
  /* 22521 */ 24, 24, 27, 27, 27, 27, 90143, 0, 921, 29315, 0, 0, 0, 0, 45, 45, 45, 45, 45, 45, 45, 45, 936, 2158592,
  /* 22545 */ 4243810, 0, 0, 0, 0, 0, 0, 0, 2211840, 0, 0, 0, 0, 2158592, 0, 921, 29315, 0, 0, 0, 0, 45, 45, 45, 45, 45,
  /* 22571 */ 45, 45, 935, 45, 45, 45, 715, 45, 45, 45, 45, 45, 45, 45, 723, 45, 45, 45, 45, 45, 1182, 45, 45, 45, 45,
  /* 22596 */ 45, 45, 45, 45, 45, 45, 430, 45, 45, 45, 45, 45, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38,
  /* 22617 */ 102439, 106538, 98347, 47, 68, 99, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538,
  /* 22634 */ 98347, 48, 69, 100, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 49, 70, 101,
  /* 22653 */ 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 50, 71, 102, 40976, 18, 36884,
  /* 22671 */ 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 51, 72, 103, 40976, 18, 36884, 45078, 24, 27,
  /* 22689 */ 90143, 94242, 38, 102439, 106538, 98347, 52, 73, 104, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38,
  /* 22707 */ 102439, 106538, 98347, 53, 74, 105, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538,
  /* 22724 */ 98347, 54, 75, 106, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 55, 76, 107,
  /* 22743 */ 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 56, 77, 108, 40976, 18, 36884,
  /* 22761 */ 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 57, 78, 109, 40976, 18, 36884, 45078, 24, 27,
  /* 22779 */ 90143, 94242, 38, 102439, 106538, 98347, 58, 79, 110, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38,
  /* 22797 */ 102439, 106538, 98347, 59, 80, 111, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538,
  /* 22814 */ 98347, 60, 81, 112, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 61, 82, 113,
  /* 22833 */ 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 62, 83, 114, 40976, 18, 36884,
  /* 22851 */ 45078, 24, 27, 90143, 94242, 38, 102439, 106538, 98347, 63, 84, 115, 40976, 18, 36884, 45078, 24, 27,
  /* 22869 */ 90143, 94242, 38, 102439, 106538, 98347, 64, 85, 116, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38,
  /* 22887 */ 102439, 106538, 98347, 65, 86, 117, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 38, 102439, 106538,
  /* 22904 */ 98347, 66, 87, 118, 40976, 18, 36884, 45078, 24, 27, 90143, 94242, 118820, 102439, 106538, 98347, 118820,
  /* 22921 */ 118820, 118820, 40976, 18, 18, 0, 0, 45078, 0, 24, 24, 24, 27, 27, 27, 27, 90143, 0, 0, 1314, 0, 0, 0, 0,
  /* 22945 */ 0, 0, 97, 97, 97, 97, 97, 1321, 97, 18, 131427, 0, 0, 0, 0, 0, 0, 362, 0, 0, 365, 0, 367, 0, 0, 1315, 0,
  /* 22972 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1360, 97, 97, 131, 94242, 0, 0, 0, 38, 102439, 0, 0,
  /* 22997 */ 106538, 98347, 28809, 45, 45, 45, 145, 149, 45, 45, 45, 45, 45, 174, 45, 179, 45, 185, 45, 188, 45, 45,
  /* 23019 */ 202, 67, 255, 67, 67, 269, 67, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 97, 97, 292, 296, 97,
  /* 23042 */ 97, 97, 97, 97, 321, 97, 326, 97, 332, 97, 18, 131427, 0, 0, 0, 0, 0, 0, 362, 0, 0, 365, 29315, 367, 646,
  /* 23067 */ 335, 97, 97, 349, 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 437, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 23092 */ 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 523, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 23118 */ 511, 67, 67, 67, 97, 97, 97, 620, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1501, 1502, 97, 793,
  /* 23143 */ 67, 67, 796, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 808, 67, 0, 0, 97, 97, 97, 97, 45, 45, 67, 67, 0, 0,
  /* 23170 */ 97, 97, 2052, 67, 67, 67, 67, 813, 67, 67, 67, 67, 67, 67, 67, 25398, 542, 13112, 544, 57889, 0, 0, 54074,
  /* 23193 */ 54074, 550, 830, 97, 97, 97, 97, 97, 97, 97, 97, 97, 315, 97, 97, 97, 97, 97, 97, 841, 97, 97, 97, 97, 97,
  /* 23218 */ 97, 97, 97, 97, 854, 97, 97, 97, 97, 97, 97, 589, 97, 97, 97, 97, 97, 97, 97, 97, 97, 867, 97, 97, 97, 97,
  /* 23244 */ 97, 97, 97, 891, 97, 97, 894, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 906, 45, 937, 45, 45, 940, 45, 45,
  /* 23269 */ 45, 45, 45, 45, 948, 45, 45, 45, 45, 45, 734, 735, 67, 737, 67, 738, 67, 740, 67, 67, 67, 45, 967, 45, 45,
  /* 23294 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 435, 45, 45, 45, 980, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 23320 */ 45, 45, 45, 45, 415, 45, 45, 67, 67, 1024, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97,
  /* 23346 */ 67, 67, 67, 67, 67, 25398, 1081, 13112, 1085, 54074, 1089, 0, 0, 0, 0, 0, 0, 363, 0, 28809, 0, 139, 45,
  /* 23369 */ 45, 45, 45, 45, 45, 1674, 45, 45, 45, 45, 45, 45, 45, 45, 67, 1913, 67, 1914, 67, 67, 67, 1918, 67, 67,
  /* 23393 */ 97, 97, 97, 97, 1118, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 630, 97, 97, 97, 97, 97, 1169, 97, 97,
  /* 23418 */ 97, 97, 97, 0, 921, 0, 1175, 0, 0, 0, 0, 45, 45, 45, 45, 45, 45, 1534, 45, 45, 45, 45, 45, 1538, 45, 45,
  /* 23444 */ 45, 45, 1233, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 742, 67, 45, 45, 1191, 45, 45, 45,
  /* 23469 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 454, 67, 67, 67, 67, 1243, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 23495 */ 67, 1251, 67, 0, 0, 97, 97, 97, 97, 45, 45, 67, 67, 2050, 0, 97, 97, 45, 45, 45, 732, 45, 45, 67, 67, 67,
  /* 23521 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 67, 67, 67, 1284, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 23547 */ 67, 772, 67, 67, 67, 1293, 67, 67, 67, 67, 67, 67, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 368, 2158592, 2158592,
  /* 23572 */ 2158592, 2404352, 2412544, 1323, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1331, 97, 97, 97, 0, 97, 97,
  /* 23594 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 1737, 97, 1364, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1373,
  /* 23619 */ 97, 18, 131427, 0, 0, 0, 0, 0, 0, 362, 0, 0, 365, 29315, 367, 647, 45, 45, 1387, 45, 45, 1391, 45, 45, 45,
  /* 23644 */ 45, 45, 45, 45, 45, 45, 45, 410, 45, 45, 45, 45, 45, 1400, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1407,
  /* 23669 */ 45, 45, 45, 45, 45, 941, 45, 943, 45, 45, 45, 45, 45, 45, 951, 45, 67, 1438, 67, 67, 67, 67, 67, 67, 67,
  /* 23694 */ 67, 67, 67, 1447, 67, 67, 67, 67, 67, 67, 782, 67, 67, 67, 67, 67, 67, 67, 67, 67, 756, 67, 67, 67, 67,
  /* 23719 */ 67, 67, 97, 1491, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1500, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97,
  /* 23745 */ 97, 97, 97, 1736, 97, 45, 45, 1541, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 677, 45, 45, 67,
  /* 23770 */ 1581, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 791, 792, 67, 67, 67, 67, 1598, 67, 1600,
  /* 23794 */ 67, 67, 67, 67, 67, 67, 67, 67, 1472, 97, 97, 97, 1727, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 23819 */ 97, 1513, 97, 97, 67, 67, 97, 1879, 97, 1881, 97, 0, 1884, 0, 97, 97, 97, 97, 0, 0, 97, 97, 97, 97, 97, 0,
  /* 23845 */ 0, 0, 1842, 97, 97, 67, 67, 67, 67, 67, 97, 97, 97, 97, 1928, 0, 0, 0, 97, 97, 97, 97, 97, 97, 45, 45, 45,
  /* 23872 */ 45, 45, 1903, 45, 45, 45, 67, 67, 67, 67, 97, 97, 97, 97, 1971, 0, 0, 97, 97, 97, 97, 0, 97, 97, 97, 97,
  /* 23898 */ 97, 97, 97, 97, 97, 0, 0, 0, 45, 45, 45, 1381, 45, 45, 45, 45, 1976, 97, 97, 97, 97, 97, 45, 45, 45, 45,
  /* 23924 */ 45, 45, 45, 45, 45, 45, 45, 45, 1747, 809, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 25398, 542, 13112,
  /* 23948 */ 544, 97, 907, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 638, 0, 0, 0, 0, 1478, 97, 97, 97, 97, 97, 97,
  /* 23974 */ 97, 97, 97, 97, 97, 1150, 97, 97, 97, 97, 67, 67, 67, 67, 1244, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 23999 */ 67, 477, 67, 67, 67, 67, 67, 67, 1294, 67, 67, 67, 67, 0, 0, 0, 0, 0, 0, 0, 0, 0, 97, 97, 97, 97, 97, 97,
  /* 24027 */ 97, 97, 97, 97, 97, 97, 97, 97, 1324, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0, 0, 1374,
  /* 24053 */ 97, 97, 97, 97, 0, 1175, 0, 45, 45, 45, 45, 45, 45, 45, 45, 945, 45, 45, 45, 45, 45, 45, 45, 45, 1908, 45,
  /* 24079 */ 45, 1910, 45, 67, 67, 67, 67, 67, 67, 67, 67, 1919, 67, 0, 0, 97, 97, 97, 97, 45, 2048, 67, 2049, 0, 0,
  /* 24104 */ 97, 2051, 45, 45, 45, 939, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 397, 45, 45, 45, 1921, 67, 67,
  /* 24129 */ 1923, 67, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 1947, 45, 1935, 0, 0, 0,
  /* 24155 */ 97, 1939, 97, 97, 1941, 97, 45, 45, 45, 45, 45, 45, 382, 389, 45, 45, 45, 45, 45, 45, 45, 45, 1810, 45,
  /* 24179 */ 45, 1812, 67, 67, 67, 67, 67, 256, 67, 67, 67, 67, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 336, 97,
  /* 24203 */ 97, 97, 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 131427, 0, 0, 0, 0, 362, 0, 365, 28809, 367, 139,
  /* 24228 */ 45, 45, 371, 373, 45, 45, 45, 955, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 413, 45, 45, 45, 457,
  /* 24253 */ 459, 67, 67, 67, 67, 67, 67, 67, 67, 473, 67, 478, 67, 67, 482, 67, 67, 485, 67, 67, 67, 67, 67, 67, 67,
  /* 24278 */ 67, 67, 67, 67, 67, 67, 97, 1828, 97, 554, 556, 97, 97, 97, 97, 97, 97, 97, 97, 570, 97, 575, 97, 97, 579,
  /* 24303 */ 97, 97, 582, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 330, 97, 97, 67, 746, 67, 67, 67, 67, 67,
  /* 24329 */ 67, 67, 67, 67, 758, 67, 67, 67, 67, 67, 67, 67, 1575, 67, 67, 67, 67, 67, 67, 67, 67, 493, 67, 67, 67,
  /* 24354 */ 67, 67, 67, 67, 97, 97, 844, 97, 97, 97, 97, 97, 97, 97, 97, 97, 856, 97, 97, 97, 0, 97, 97, 97, 97, 97,
  /* 24380 */ 97, 97, 97, 1735, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97, 1642, 97, 1644, 97, 97, 890, 97, 97, 97, 97,
  /* 24405 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 67, 67, 67, 67, 1065, 1066, 67, 67, 67, 67, 67, 67, 67,
  /* 24431 */ 67, 67, 67, 532, 67, 67, 67, 67, 67, 67, 67, 1451, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 24456 */ 496, 67, 67, 97, 97, 1505, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 593, 97, 97, 0, 1474, 0,
  /* 24481 */ 1476, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1617, 97, 97, 1635, 0, 1637, 97, 97, 97, 97, 97, 97, 97,
  /* 24506 */ 97, 97, 97, 97, 885, 97, 97, 97, 97, 67, 67, 1704, 67, 67, 67, 67, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 24531 */ 565, 572, 97, 97, 97, 97, 97, 97, 97, 97, 1832, 0, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 97, 97,
  /* 24557 */ 45, 45, 45, 1946, 45, 45, 67, 67, 67, 67, 67, 97, 1926, 97, 1927, 97, 0, 0, 0, 97, 97, 1934, 2043, 0, 0,
  /* 24582 */ 97, 97, 97, 2047, 45, 45, 67, 67, 0, 1832, 97, 97, 45, 45, 45, 981, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 24607 */ 45, 45, 45, 1227, 45, 45, 45, 131427, 0, 0, 0, 0, 362, 0, 365, 28809, 367, 139, 45, 45, 372, 45, 45, 45,
  /* 24631 */ 45, 1661, 1662, 45, 45, 45, 45, 45, 1666, 45, 45, 45, 45, 45, 1673, 45, 1675, 45, 45, 45, 45, 45, 45, 45,
  /* 24655 */ 67, 1426, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1275, 67, 67, 67, 67, 67, 45, 418, 45, 45, 420, 45, 45,
  /* 24680 */ 423, 45, 45, 45, 45, 45, 45, 45, 45, 959, 45, 45, 962, 45, 45, 45, 45, 458, 67, 67, 67, 67, 67, 67, 67,
  /* 24705 */ 67, 67, 67, 67, 67, 67, 67, 483, 67, 67, 67, 67, 504, 67, 67, 506, 67, 67, 509, 67, 67, 67, 67, 67, 67,
  /* 24730 */ 67, 528, 67, 67, 67, 67, 67, 67, 67, 67, 1287, 67, 67, 67, 67, 67, 67, 67, 555, 97, 97, 97, 97, 97, 97,
  /* 24755 */ 97, 97, 97, 97, 97, 97, 97, 97, 580, 97, 97, 97, 97, 601, 97, 97, 603, 97, 97, 606, 97, 97, 97, 97, 97,
  /* 24780 */ 97, 848, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1498, 97, 97, 97, 97, 97, 97, 45, 45, 714, 45, 45, 45, 45,
  /* 24805 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 989, 990, 45, 67, 67, 67, 67, 67, 1011, 67, 67, 67, 67, 1015, 67, 67,
  /* 24830 */ 67, 67, 67, 67, 67, 753, 67, 67, 67, 67, 67, 67, 67, 67, 467, 67, 67, 67, 67, 67, 67, 67, 45, 45, 1179,
  /* 24855 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1003, 1004, 67, 1217, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 24880 */ 45, 45, 45, 45, 45, 45, 45, 728, 67, 1461, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1034,
  /* 24905 */ 67, 97, 1516, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 871, 97, 67, 67, 67, 1705, 67, 67,
  /* 24930 */ 67, 97, 97, 97, 97, 97, 97, 97, 97, 97, 567, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1715, 97, 97, 97, 97,
  /* 24956 */ 97, 97, 97, 97, 97, 0, 0, 0, 45, 45, 1380, 45, 45, 45, 45, 45, 67, 67, 97, 97, 97, 97, 97, 0, 0, 0, 97,
  /* 24983 */ 1887, 97, 97, 0, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 2006, 45, 45, 1907, 45, 45, 45, 45, 45, 67, 67, 67,
  /* 25009 */ 67, 67, 67, 67, 67, 67, 1920, 67, 97, 0, 2035, 97, 97, 97, 97, 97, 45, 45, 45, 45, 67, 67, 67, 1428, 67,
  /* 25034 */ 67, 67, 67, 67, 67, 1435, 67, 0, 94242, 0, 0, 0, 38, 102439, 0, 0, 106538, 98347, 28809, 45, 45, 45, 146,
  /* 25057 */ 45, 152, 45, 45, 165, 45, 175, 45, 180, 45, 45, 187, 190, 195, 45, 203, 254, 257, 262, 67, 270, 67, 67, 0,
  /* 25081 */ 24850, 12564, 0, 0, 0, 281, 28809, 53531, 97, 97, 97, 293, 97, 299, 97, 97, 312, 97, 322, 97, 327, 97, 97,
  /* 25104 */ 334, 337, 342, 97, 350, 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 67, 484, 67, 67, 67, 67, 67, 67,
  /* 25129 */ 67, 67, 67, 67, 67, 67, 67, 499, 97, 581, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 596, 648,
  /* 25154 */ 45, 650, 45, 651, 45, 653, 45, 45, 45, 657, 45, 45, 45, 45, 45, 45, 1954, 67, 67, 67, 1958, 67, 67, 67,
  /* 25178 */ 67, 67, 67, 67, 768, 67, 67, 67, 67, 67, 67, 67, 67, 769, 67, 67, 67, 67, 67, 67, 67, 680, 45, 45, 45, 45,
  /* 25204 */ 45, 45, 45, 45, 688, 689, 691, 45, 45, 45, 45, 45, 983, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 947, 45,
  /* 25229 */ 45, 45, 45, 952, 45, 45, 698, 699, 45, 45, 702, 703, 45, 45, 45, 45, 45, 45, 45, 711, 744, 67, 67, 67, 67,
  /* 25254 */ 67, 67, 67, 67, 67, 757, 67, 67, 67, 67, 761, 67, 67, 67, 67, 765, 67, 767, 67, 67, 67, 67, 67, 67, 67,
  /* 25279 */ 67, 775, 776, 778, 67, 67, 67, 67, 67, 67, 785, 786, 67, 67, 789, 790, 67, 67, 67, 67, 67, 67, 1442, 67,
  /* 25303 */ 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97, 1775, 97, 97, 97, 67, 67, 67, 67, 67, 798, 67, 67, 67, 802,
  /* 25328 */ 67, 67, 67, 67, 67, 67, 67, 67, 1465, 67, 67, 1468, 67, 67, 1471, 67, 67, 810, 67, 67, 67, 67, 67, 67, 67,
  /* 25353 */ 67, 67, 821, 25398, 542, 13112, 544, 57889, 0, 0, 54074, 54074, 550, 0, 833, 97, 835, 97, 836, 97, 838,
  /* 25374 */ 97, 97, 0, 0, 97, 97, 97, 2002, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 1740, 45, 45, 45, 1744, 45, 45,
  /* 25399 */ 45, 97, 842, 97, 97, 97, 97, 97, 97, 97, 97, 97, 855, 97, 97, 97, 97, 0, 1717, 1718, 97, 97, 97, 97, 97,
  /* 25424 */ 1722, 97, 0, 0, 859, 97, 97, 97, 97, 863, 97, 865, 97, 97, 97, 97, 97, 97, 97, 97, 604, 97, 97, 97, 97,
  /* 25449 */ 97, 97, 97, 873, 874, 876, 97, 97, 97, 97, 97, 97, 883, 884, 97, 97, 887, 888, 97, 18, 131427, 0, 0, 0, 0,
  /* 25474 */ 0, 0, 362, 225280, 0, 365, 0, 367, 0, 45, 45, 45, 1531, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1199,
  /* 25499 */ 45, 45, 45, 45, 45, 97, 97, 908, 97, 97, 97, 97, 97, 97, 97, 97, 97, 919, 638, 0, 0, 0, 0, 2158877,
  /* 25523 */ 2158877, 2158877, 2158877, 2158877, 2425117, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877,
  /* 25534 */ 2597149, 2158877, 2158877, 2158877, 2158877, 2158877, 2158877, 2642205, 2158877, 2158877, 2158877,
  /* 25545 */ 2158877, 2158877, 3158301, 0, 2375818, 2379914, 2158730, 2158730, 2420874, 2158730, 2449546, 2158730,
  /* 25557 */ 2158730, 953, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 965, 978, 45, 45, 45, 45, 45,
  /* 25581 */ 45, 985, 45, 45, 45, 45, 45, 45, 45, 45, 971, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 1027, 67,
  /* 25606 */ 1029, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1455, 67, 67, 67, 67, 67, 67, 67, 1077, 1078, 67, 67, 25398, 0,
  /* 25630 */ 13112, 0, 54074, 0, 0, 0, 0, 0, 0, 0, 0, 366, 0, 139, 2158730, 2158730, 2158730, 2404490, 2412682, 1113,
  /* 25650 */ 97, 97, 97, 97, 97, 97, 1121, 97, 1123, 97, 97, 97, 97, 97, 97, 0, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 25676 */ 45, 45, 45, 45, 1540, 1155, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 615, 1168, 97, 97,
  /* 25701 */ 1171, 1172, 97, 97, 0, 921, 0, 1175, 0, 0, 0, 0, 45, 45, 45, 45, 45, 1533, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 25727 */ 45, 1663, 45, 45, 45, 45, 45, 45, 45, 45, 45, 183, 45, 45, 45, 45, 201, 45, 45, 45, 1219, 45, 45, 45, 45,
  /* 25752 */ 45, 45, 45, 1226, 45, 45, 45, 45, 45, 168, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 427, 45, 45, 45, 45,
  /* 25777 */ 45, 45, 45, 1231, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1242, 67,
  /* 25802 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1046, 67, 67, 1254, 67, 1256, 67, 67, 67, 67, 67, 67,
  /* 25827 */ 67, 67, 67, 67, 67, 67, 806, 807, 67, 67, 97, 1336, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 25852 */ 97, 1111, 97, 97, 97, 97, 97, 1351, 97, 97, 97, 1354, 97, 97, 97, 1359, 97, 97, 97, 0, 97, 97, 97, 97,
  /* 25876 */ 1640, 97, 97, 97, 97, 97, 97, 97, 897, 97, 97, 97, 902, 97, 97, 97, 97, 97, 97, 97, 97, 1366, 97, 97, 97,
  /* 25901 */ 97, 97, 97, 97, 1371, 97, 97, 97, 0, 97, 97, 97, 1730, 97, 97, 97, 97, 97, 97, 97, 97, 915, 97, 97, 97,
  /* 25926 */ 97, 0, 360, 0, 67, 67, 67, 1440, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1017, 67, 1019, 67, 67,
  /* 25951 */ 67, 67, 67, 1453, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1459, 97, 97, 97, 1493, 97, 97, 97, 97, 97, 97,
  /* 25976 */ 97, 97, 97, 97, 97, 97, 97, 1525, 97, 97, 97, 97, 97, 97, 1507, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 26001 */ 1514, 67, 67, 67, 67, 1584, 67, 67, 67, 67, 67, 1590, 67, 67, 67, 67, 67, 67, 67, 783, 67, 67, 67, 788,
  /* 26025 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 1599, 1601, 67, 67, 67, 1604, 67, 1606, 1607, 67, 1472, 0, 1474, 0,
  /* 26048 */ 1476, 0, 97, 97, 97, 97, 97, 97, 1614, 97, 97, 97, 97, 45, 45, 1850, 45, 45, 45, 45, 1855, 45, 45, 45, 45,
  /* 26073 */ 45, 1222, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1229, 97, 1618, 97, 97, 97, 97, 97, 97, 97, 1625, 97, 97,
  /* 26097 */ 97, 97, 97, 0, 1175, 0, 45, 45, 45, 45, 45, 45, 45, 45, 447, 45, 45, 45, 45, 45, 67, 67, 1633, 97, 97, 0,
  /* 26123 */ 97, 97, 97, 97, 97, 97, 97, 97, 1643, 1645, 97, 97, 0, 0, 97, 97, 1784, 97, 97, 97, 0, 0, 97, 97, 0, 97,
  /* 26149 */ 1894, 1895, 97, 1897, 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 656, 45, 45, 45, 45, 45, 45, 97, 1648, 97,
  /* 26173 */ 1650, 1651, 97, 0, 45, 45, 45, 1654, 45, 45, 45, 45, 45, 169, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 658,
  /* 26198 */ 45, 45, 45, 45, 664, 45, 45, 1659, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1187, 45, 45, 1669,
  /* 26223 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 1005, 67, 67, 1681, 67, 67, 67, 67, 67, 67,
  /* 26248 */ 67, 1686, 67, 67, 67, 67, 67, 67, 67, 784, 67, 67, 67, 67, 67, 67, 67, 67, 1055, 67, 67, 67, 67, 1060, 67,
  /* 26273 */ 67, 97, 97, 1713, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0, 0, 1378, 45, 45, 45, 45, 45, 45, 45,
  /* 26299 */ 408, 45, 45, 45, 45, 45, 45, 45, 45, 1547, 45, 1549, 45, 45, 45, 45, 45, 97, 97, 1780, 0, 97, 97, 97, 97,
  /* 26324 */ 97, 97, 0, 0, 97, 97, 0, 97, 97, 97, 45, 45, 2027, 2028, 45, 45, 67, 67, 2031, 2032, 67, 45, 45, 1804, 45,
  /* 26349 */ 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 1917, 67, 67, 67, 67, 67, 67, 67, 1819, 67, 67, 67,
  /* 26374 */ 67, 67, 67, 67, 67, 97, 97, 97, 1708, 97, 97, 97, 97, 97, 45, 45, 1862, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 26399 */ 67, 67, 67, 67, 67, 497, 67, 67, 67, 1877, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 0, 0, 97, 97, 97,
  /* 26426 */ 97, 97, 1839, 0, 0, 97, 97, 97, 97, 1936, 0, 0, 97, 97, 97, 97, 97, 97, 1943, 1944, 1945, 45, 45, 45, 45,
  /* 26451 */ 670, 45, 45, 45, 45, 674, 45, 45, 45, 45, 678, 45, 1948, 45, 1950, 45, 45, 45, 45, 1955, 1956, 1957, 67,
  /* 26474 */ 67, 67, 1960, 67, 1962, 67, 67, 67, 67, 1967, 1968, 1969, 97, 0, 0, 0, 97, 97, 1974, 97, 0, 1936, 0, 97,
  /* 26498 */ 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 1906, 0, 1977, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45,
  /* 26524 */ 45, 45, 45, 45, 45, 1746, 45, 45, 45, 45, 2011, 67, 67, 2013, 67, 67, 67, 2017, 97, 97, 0, 0, 2021, 97,
  /* 26548 */ 8192, 97, 97, 2025, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 1916, 67, 67, 67, 67, 0, 94242, 0, 0, 0,
  /* 26573 */ 38, 102439, 0, 0, 106538, 98347, 28809, 45, 45, 140, 45, 45, 45, 1180, 45, 45, 45, 45, 1184, 45, 45, 45,
  /* 26595 */ 45, 45, 45, 45, 387, 45, 392, 45, 45, 396, 45, 45, 399, 45, 45, 67, 207, 67, 67, 67, 67, 67, 67, 236, 67,
  /* 26620 */ 67, 67, 67, 67, 67, 67, 800, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1603, 67, 67, 67, 67, 67, 0, 97, 97, 287,
  /* 26646 */ 97, 97, 97, 97, 97, 97, 316, 97, 97, 97, 97, 97, 97, 0, 45, 45, 45, 45, 45, 45, 45, 1656, 1657, 45, 376,
  /* 26671 */ 45, 45, 45, 45, 45, 388, 45, 45, 45, 45, 45, 45, 45, 45, 1406, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67,
  /* 26697 */ 462, 67, 67, 67, 67, 67, 474, 67, 67, 67, 67, 67, 67, 67, 817, 67, 67, 67, 67, 25398, 542, 13112, 544, 97,
  /* 26721 */ 97, 97, 97, 559, 97, 97, 97, 97, 97, 571, 97, 97, 97, 97, 97, 97, 896, 97, 97, 97, 900, 97, 97, 97, 97,
  /* 26746 */ 97, 97, 912, 914, 97, 97, 97, 97, 97, 0, 0, 0, 45, 45, 45, 45, 45, 45, 45, 45, 391, 45, 45, 45, 45, 45,
  /* 26772 */ 45, 45, 45, 713, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 662, 45, 1140, 97, 97, 97, 97,
  /* 26797 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 636, 67, 67, 1283, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 26823 */ 67, 67, 513, 67, 67, 1363, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 889, 97, 97, 97,
  /* 26848 */ 1714, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0, 926, 45, 45, 45, 45, 45, 45, 45, 45, 672, 45, 45, 45,
  /* 26874 */ 45, 45, 45, 45, 45, 686, 45, 45, 45, 45, 45, 45, 45, 45, 944, 45, 45, 45, 45, 45, 45, 45, 45, 1676, 45,
  /* 26899 */ 45, 45, 45, 45, 45, 67, 97, 97, 97, 1833, 0, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 97, 97, 45, 45,
  /* 26926 */ 45, 45, 1902, 45, 45, 45, 45, 45, 957, 45, 45, 45, 45, 961, 45, 963, 45, 45, 45, 67, 97, 2034, 0, 97, 97,
  /* 26951 */ 97, 97, 97, 2040, 45, 45, 45, 2042, 67, 67, 67, 67, 67, 67, 1574, 67, 67, 67, 67, 67, 1578, 67, 67, 67,
  /* 26975 */ 67, 67, 67, 799, 67, 67, 67, 804, 67, 67, 67, 67, 67, 67, 67, 1298, 0, 0, 0, 1304, 0, 0, 0, 1310, 132,
  /* 27000 */ 94242, 0, 0, 0, 38, 102439, 0, 0, 106538, 98347, 28809, 45, 45, 45, 45, 45, 1414, 45, 45, 45, 45, 45, 45,
  /* 27023 */ 45, 45, 45, 45, 428, 45, 45, 45, 45, 45, 57889, 0, 0, 54074, 54074, 550, 831, 97, 97, 97, 97, 97, 97, 97,
  /* 27047 */ 97, 97, 568, 97, 97, 97, 97, 578, 97, 45, 45, 968, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 27072 */ 1228, 45, 45, 67, 67, 67, 67, 67, 25398, 1082, 13112, 1086, 54074, 1090, 0, 0, 0, 0, 0, 0, 364, 0, 0, 0,
  /* 27096 */ 139, 2158592, 2158592, 2158592, 2404352, 2412544, 67, 67, 67, 67, 1464, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 27115 */ 67, 67, 67, 510, 67, 67, 67, 67, 97, 97, 97, 97, 1519, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 918,
  /* 27140 */ 97, 0, 0, 0, 0, 1528, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 976, 45, 1554, 45, 45, 45,
  /* 27166 */ 45, 45, 45, 45, 45, 1562, 45, 45, 1565, 45, 45, 45, 45, 683, 45, 45, 45, 687, 45, 45, 692, 45, 45, 45, 45,
  /* 27191 */ 45, 1953, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1014, 67, 67, 67, 67, 67, 67, 1568, 67, 67, 67, 67, 67,
  /* 27216 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 0, 67, 67, 67, 67, 67, 1585, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 27242 */ 67, 1594, 97, 97, 1649, 97, 97, 97, 0, 45, 45, 1653, 45, 45, 45, 45, 45, 45, 383, 45, 45, 45, 45, 45, 45,
  /* 27267 */ 45, 45, 45, 986, 45, 45, 45, 45, 45, 45, 45, 45, 1670, 45, 1672, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 27292 */ 67, 736, 67, 67, 67, 67, 67, 741, 67, 67, 67, 1680, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 27317 */ 67, 1074, 67, 67, 67, 1692, 67, 67, 67, 67, 67, 67, 67, 1697, 67, 1699, 67, 67, 67, 67, 67, 67, 1012, 67,
  /* 27341 */ 67, 67, 67, 67, 67, 67, 67, 67, 468, 475, 67, 67, 67, 67, 67, 67, 1769, 67, 67, 67, 67, 67, 67, 67, 97,
  /* 27366 */ 97, 97, 97, 97, 97, 97, 624, 97, 97, 97, 97, 97, 97, 634, 97, 97, 1792, 97, 97, 97, 97, 97, 97, 97, 45,
  /* 27391 */ 45, 45, 45, 45, 45, 45, 958, 45, 45, 45, 45, 45, 45, 964, 45, 150, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 27417 */ 45, 45, 45, 45, 45, 977, 204, 45, 67, 67, 67, 217, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 787, 67, 67,
  /* 27442 */ 67, 67, 67, 67, 67, 67, 67, 67, 271, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 97, 97, 97, 351,
  /* 27466 */ 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 45, 45, 938, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 27492 */ 45, 1398, 45, 45, 45, 153, 45, 161, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 660, 661, 45, 45, 205,
  /* 27517 */ 45, 67, 67, 67, 67, 220, 67, 228, 67, 67, 67, 67, 67, 67, 67, 0, 0, 0, 0, 0, 280, 94, 0, 0, 67, 67, 67,
  /* 27544 */ 67, 67, 272, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 97, 97, 97, 352, 97, 0, 40976, 0, 18, 18,
  /* 27568 */ 24, 24, 27, 27, 27, 45, 439, 45, 45, 45, 45, 45, 445, 45, 45, 45, 452, 45, 45, 67, 67, 212, 216, 67, 67,
  /* 27593 */ 67, 67, 67, 241, 67, 246, 67, 252, 67, 67, 486, 67, 67, 67, 67, 67, 67, 67, 494, 67, 67, 67, 67, 67, 67,
  /* 27618 */ 67, 1245, 67, 67, 67, 67, 67, 67, 67, 67, 1013, 67, 67, 1016, 67, 67, 67, 67, 67, 521, 67, 67, 525, 67,
  /* 27642 */ 67, 67, 67, 67, 531, 67, 67, 67, 538, 67, 0, 0, 2046, 97, 97, 97, 45, 45, 67, 67, 0, 0, 97, 97, 45, 45,
  /* 27668 */ 45, 1192, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1418, 45, 45, 1421, 97, 97, 583, 97, 97, 97, 97,
  /* 27693 */ 97, 97, 97, 591, 97, 97, 97, 97, 97, 97, 913, 97, 97, 97, 97, 97, 97, 0, 0, 0, 45, 45, 45, 45, 45, 45, 45,
  /* 27720 */ 1384, 97, 618, 97, 97, 622, 97, 97, 97, 97, 97, 628, 97, 97, 97, 635, 97, 18, 131427, 0, 0, 0, 639, 0,
  /* 27744 */ 132, 362, 0, 0, 365, 29315, 367, 0, 921, 29315, 0, 0, 0, 0, 45, 45, 45, 45, 932, 45, 45, 45, 45, 45, 1544,
  /* 27769 */ 45, 45, 45, 45, 45, 1550, 45, 45, 45, 45, 45, 1194, 45, 1196, 45, 45, 45, 45, 45, 45, 45, 45, 999, 45, 45,
  /* 27794 */ 45, 45, 45, 67, 67, 45, 45, 667, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1408, 45, 45, 45,
  /* 27819 */ 696, 45, 45, 45, 701, 45, 45, 45, 45, 45, 45, 45, 45, 710, 45, 45, 45, 1220, 45, 45, 45, 45, 45, 45, 45,
  /* 27844 */ 45, 45, 45, 45, 45, 194, 45, 45, 45, 729, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 27870 */ 67, 67, 67, 67, 67, 67, 67, 797, 67, 67, 67, 67, 67, 67, 805, 67, 67, 67, 67, 67, 67, 67, 1587, 67, 1589,
  /* 27895 */ 67, 67, 67, 67, 67, 67, 67, 67, 1763, 67, 67, 67, 67, 67, 67, 67, 0, 0, 0, 0, 0, 0, 2162968, 0, 0, 67, 67,
  /* 27922 */ 67, 67, 67, 814, 816, 67, 67, 67, 67, 67, 25398, 542, 13112, 544, 67, 67, 1008, 67, 67, 67, 67, 67, 67,
  /* 27945 */ 67, 67, 67, 67, 67, 1020, 67, 0, 97, 45, 67, 0, 97, 45, 67, 0, 97, 45, 67, 97, 0, 0, 97, 97, 97, 97, 97,
  /* 27972 */ 45, 45, 45, 45, 67, 67, 67, 67, 1429, 67, 1430, 67, 67, 67, 67, 67, 1062, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 27997 */ 67, 67, 67, 67, 67, 67, 67, 518, 1076, 67, 67, 67, 67, 25398, 0, 13112, 0, 54074, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 28023 */ 28809, 0, 139, 45, 45, 45, 45, 45, 97, 97, 97, 97, 1102, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1124,
  /* 28048 */ 97, 1126, 97, 97, 1114, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1112, 97, 97, 1156,
  /* 28072 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 594, 97, 97, 97, 97, 1170, 97, 97, 97, 97, 0, 921, 0,
  /* 28098 */ 0, 0, 0, 0, 0, 45, 45, 45, 45, 1532, 45, 45, 45, 45, 1536, 45, 45, 45, 45, 45, 172, 45, 45, 45, 45, 45,
  /* 28124 */ 45, 45, 45, 45, 45, 706, 45, 45, 709, 45, 45, 1177, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 28149 */ 45, 45, 1202, 45, 1204, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1215, 45, 45, 45, 1232, 45, 45,
  /* 28173 */ 45, 45, 45, 45, 45, 67, 1237, 67, 67, 67, 67, 67, 67, 1053, 1054, 67, 67, 67, 67, 67, 67, 1061, 67, 67,
  /* 28197 */ 1282, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1289, 67, 67, 67, 1292, 97, 97, 97, 97, 1339, 97, 97, 97, 97,
  /* 28221 */ 97, 97, 1344, 97, 97, 97, 97, 45, 1849, 45, 1851, 45, 45, 45, 45, 45, 45, 45, 45, 721, 45, 45, 45, 45, 45,
  /* 28246 */ 726, 45, 1385, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1188, 45, 45, 1401, 1402, 45,
  /* 28270 */ 45, 45, 45, 1405, 45, 45, 45, 45, 45, 45, 45, 45, 1752, 45, 45, 45, 45, 45, 67, 67, 1410, 45, 45, 45,
  /* 28294 */ 1413, 45, 1415, 45, 45, 45, 45, 45, 45, 1419, 45, 45, 45, 45, 1806, 45, 45, 45, 45, 45, 45, 67, 67, 67,
  /* 28318 */ 67, 67, 67, 67, 97, 97, 2019, 0, 97, 67, 67, 67, 1452, 67, 67, 67, 67, 67, 67, 67, 67, 1457, 67, 67, 67,
  /* 28343 */ 67, 67, 67, 1259, 67, 67, 67, 67, 67, 67, 1264, 67, 67, 1460, 67, 1462, 67, 67, 67, 67, 67, 67, 1466, 67,
  /* 28367 */ 67, 67, 67, 67, 67, 67, 67, 1588, 67, 67, 67, 67, 67, 67, 67, 0, 1300, 0, 0, 0, 1306, 0, 0, 0, 97, 97, 97,
  /* 28394 */ 1506, 97, 97, 97, 97, 97, 97, 97, 97, 1512, 97, 97, 97, 0, 1728, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 28419 */ 97, 901, 97, 97, 97, 97, 1515, 97, 1517, 97, 97, 97, 97, 97, 97, 1521, 97, 97, 97, 97, 97, 97, 0, 45,
  /* 28443 */ 1652, 45, 45, 45, 1655, 45, 45, 45, 45, 45, 1542, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 28467 */ 1552, 1553, 45, 45, 45, 1556, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 693, 45, 45, 45, 67, 67,
  /* 28492 */ 67, 67, 1572, 67, 67, 67, 67, 1576, 67, 67, 67, 67, 67, 67, 67, 67, 1602, 67, 67, 1605, 67, 67, 67, 0, 67,
  /* 28517 */ 1582, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1580, 67, 67, 1596, 67, 67, 67, 67, 67, 67,
  /* 28542 */ 67, 67, 67, 67, 67, 67, 67, 0, 542, 0, 544, 67, 67, 67, 67, 1759, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 28568 */ 67, 533, 67, 67, 67, 67, 67, 67, 67, 1770, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 97, 1777, 97, 97, 97,
  /* 28593 */ 1793, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 998, 45, 45, 1001, 1002, 45, 45, 67, 67, 45, 1861,
  /* 28617 */ 45, 67, 67, 67, 67, 67, 67, 67, 67, 1871, 67, 1873, 1874, 67, 0, 97, 45, 67, 0, 97, 45, 67, 16384, 97, 45,
  /* 28642 */ 67, 97, 0, 0, 0, 1473, 0, 1082, 0, 0, 0, 1475, 0, 1086, 0, 0, 0, 1477, 1876, 67, 97, 97, 97, 97, 97, 1883,
  /* 28668 */ 0, 1885, 97, 97, 97, 1889, 0, 0, 0, 286, 0, 0, 0, 286, 0, 2367488, 2158592, 2158592, 2158592, 2158592,
  /* 28688 */ 2158592, 2158592, 0, 40976, 0, 18, 18, 24, 24, 126, 126, 126, 2053, 0, 2055, 45, 67, 0, 97, 45, 67, 0, 97,
  /* 28711 */ 45, 67, 97, 0, 0, 97, 97, 97, 2039, 97, 45, 45, 45, 45, 67, 67, 67, 67, 67, 226, 67, 67, 67, 67, 67, 67,
  /* 28737 */ 67, 67, 1246, 67, 67, 1249, 1250, 67, 67, 67, 132, 94242, 0, 0, 0, 38, 102439, 0, 0, 106538, 98347, 28809,
  /* 28759 */ 45, 45, 141, 45, 45, 45, 1403, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1186, 45, 45, 1189, 45, 45,
  /* 28784 */ 155, 45, 45, 45, 45, 45, 45, 45, 45, 45, 191, 45, 45, 45, 45, 700, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 28810 */ 45, 1753, 45, 45, 45, 67, 67, 45, 45, 67, 208, 67, 67, 67, 222, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1764,
  /* 28835 */ 67, 67, 67, 67, 67, 67, 67, 258, 67, 67, 67, 67, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 97,
  /* 28859 */ 288, 97, 97, 97, 302, 97, 97, 97, 97, 97, 97, 97, 97, 97, 627, 97, 97, 97, 97, 97, 97, 338, 97, 97, 97,
  /* 28884 */ 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 131427, 0, 0, 0, 0, 362, 0, 365, 28809, 367, 139, 45,
  /* 28908 */ 370, 45, 45, 45, 45, 716, 45, 45, 45, 45, 45, 722, 45, 45, 45, 45, 45, 45, 1912, 67, 67, 67, 67, 67, 67,
  /* 28933 */ 67, 67, 67, 819, 67, 67, 25398, 542, 13112, 544, 45, 403, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 28957 */ 45, 45, 1409, 45, 67, 67, 67, 67, 489, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 771, 67, 67, 67, 67,
  /* 28982 */ 520, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 534, 67, 67, 67, 67, 67, 67, 1271, 67, 67, 67, 1274, 67,
  /* 29007 */ 67, 67, 1279, 67, 67, 24850, 24850, 12564, 12564, 0, 57889, 0, 0, 0, 53531, 53531, 367, 286, 97, 553, 97,
  /* 29028 */ 97, 97, 97, 586, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1138, 97, 97, 97, 97, 617, 97, 97, 97, 97,
  /* 29053 */ 97, 97, 97, 97, 97, 97, 97, 631, 97, 97, 97, 0, 1834, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 97,
  /* 29079 */ 353, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 45, 45, 668, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 29105 */ 45, 724, 45, 45, 45, 45, 45, 682, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 949, 45, 45, 45, 67,
  /* 29131 */ 67, 747, 748, 67, 67, 67, 67, 755, 67, 67, 67, 67, 67, 67, 67, 0, 0, 0, 1302, 0, 0, 0, 1308, 0, 67, 794,
  /* 29157 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1701, 67, 97, 97, 97, 845, 846, 97, 97, 97, 97,
  /* 29182 */ 853, 97, 97, 97, 97, 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 97, 97, 892, 97, 97, 97, 97, 97, 97,
  /* 29208 */ 97, 97, 97, 97, 97, 97, 97, 610, 97, 97, 45, 992, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67,
  /* 29234 */ 67, 1239, 67, 67, 67, 1063, 67, 67, 67, 67, 67, 1068, 67, 67, 67, 67, 67, 67, 67, 0, 0, 1301, 0, 0, 0,
  /* 29259 */ 1307, 0, 0, 97, 1141, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1152, 97, 97, 0, 0, 97, 97, 2001, 0, 97,
  /* 29285 */ 2003, 97, 97, 97, 45, 45, 45, 1739, 45, 45, 45, 1742, 45, 45, 45, 45, 45, 97, 97, 97, 97, 1157, 97, 97,
  /* 29309 */ 97, 97, 97, 1162, 97, 97, 97, 97, 97, 97, 1145, 97, 97, 97, 97, 97, 1151, 97, 97, 97, 1253, 67, 67, 67,
  /* 29333 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 539, 45, 1423, 45, 45, 67, 67, 67, 67, 67, 67, 67, 1431,
  /* 29358 */ 67, 67, 67, 67, 67, 67, 67, 1695, 67, 67, 67, 67, 67, 1700, 67, 1702, 67, 67, 1439, 67, 67, 67, 67, 67,
  /* 29382 */ 67, 67, 67, 67, 67, 67, 67, 67, 514, 67, 67, 97, 97, 1492, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 29408 */ 97, 611, 97, 97, 1703, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 97, 97, 97, 97, 852, 97, 97, 97, 97,
  /* 29433 */ 97, 97, 45, 1949, 45, 1951, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 1961, 67, 0, 97, 45, 67, 0, 97, 2060,
  /* 29458 */ 2061, 0, 2062, 45, 67, 97, 0, 0, 2036, 97, 97, 97, 97, 45, 45, 45, 45, 67, 67, 67, 67, 67, 223, 67, 67,
  /* 29483 */ 237, 67, 67, 67, 67, 67, 67, 67, 1272, 67, 67, 67, 67, 67, 67, 67, 67, 507, 67, 67, 67, 67, 67, 67, 67,
  /* 29508 */ 1963, 67, 67, 67, 97, 97, 97, 97, 0, 1972, 0, 97, 97, 97, 1975, 0, 921, 29315, 0, 0, 0, 0, 45, 45, 45,
  /* 29533 */ 931, 45, 45, 45, 45, 45, 407, 45, 45, 45, 45, 45, 45, 45, 45, 45, 417, 45, 45, 1989, 67, 67, 67, 67, 67,
  /* 29558 */ 67, 67, 67, 67, 67, 67, 1996, 97, 18, 131427, 0, 0, 360, 0, 0, 0, 362, 0, 0, 365, 29315, 367, 0, 921,
  /* 29582 */ 29315, 0, 0, 0, 0, 45, 45, 930, 45, 45, 45, 45, 45, 45, 444, 45, 45, 45, 45, 45, 45, 45, 67, 67, 97, 97,
  /* 29608 */ 1998, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 1985, 45, 1986, 45, 45, 45, 156, 45,
  /* 29633 */ 45, 170, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 675, 45, 45, 45, 45, 679, 131427, 0, 358, 0, 0, 362, 0,
  /* 29658 */ 365, 28809, 367, 139, 45, 45, 45, 45, 45, 381, 45, 45, 45, 45, 45, 45, 45, 45, 45, 400, 45, 45, 419, 45,
  /* 29682 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 436, 67, 67, 67, 67, 67, 505, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 29708 */ 67, 67, 820, 67, 25398, 542, 13112, 544, 67, 67, 522, 67, 67, 67, 67, 67, 529, 67, 67, 67, 67, 67, 67, 67,
  /* 29732 */ 0, 1299, 0, 0, 0, 1305, 0, 0, 0, 97, 97, 619, 97, 97, 97, 97, 97, 626, 97, 97, 97, 97, 97, 97, 97, 1105,
  /* 29758 */ 97, 97, 97, 97, 1109, 97, 97, 97, 67, 67, 67, 67, 749, 67, 67, 67, 67, 67, 67, 67, 67, 67, 760, 67, 0, 97,
  /* 29784 */ 45, 67, 2058, 97, 45, 67, 0, 97, 45, 67, 97, 0, 0, 97, 97, 97, 97, 97, 45, 45, 45, 2041, 67, 67, 67, 67,
  /* 29810 */ 67, 780, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 516, 67, 67, 97, 97, 97, 878, 97, 97, 97, 97,
  /* 29836 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 1629, 97, 0, 45, 979, 45, 45, 45, 45, 984, 45, 45, 45, 45, 45, 45, 45,
  /* 29862 */ 45, 45, 1198, 45, 45, 45, 45, 45, 45, 67, 1023, 67, 67, 67, 67, 1028, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 29887 */ 470, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 25398, 0, 13112, 0, 54074, 0, 0, 0, 1094, 0, 0, 0, 1092,
  /* 29912 */ 1315, 0, 0, 0, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1486, 97, 1489, 97, 97, 97, 1117, 97, 97, 97, 97,
  /* 29937 */ 1122, 97, 97, 97, 97, 97, 97, 97, 1146, 97, 97, 97, 97, 97, 97, 97, 97, 881, 97, 97, 97, 886, 97, 97, 97,
  /* 29962 */ 1311, 0, 0, 0, 0, 0, 0, 0, 0, 97, 97, 97, 97, 97, 97, 97, 1615, 97, 97, 97, 97, 97, 1619, 97, 97, 97, 97,
  /* 29989 */ 97, 97, 97, 97, 97, 97, 97, 97, 1631, 97, 97, 1847, 97, 45, 45, 45, 45, 1852, 45, 45, 45, 45, 45, 45, 45,
  /* 30014 */ 1235, 45, 45, 45, 67, 67, 67, 67, 67, 1868, 67, 67, 67, 1872, 67, 67, 67, 67, 67, 97, 97, 97, 97, 1882, 0,
  /* 30039 */ 0, 0, 97, 97, 97, 97, 0, 1891, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 1929, 0, 0, 97, 97, 97, 97, 97, 97,
  /* 30066 */ 45, 1900, 45, 1901, 45, 45, 45, 1905, 45, 67, 2054, 97, 45, 67, 0, 97, 45, 67, 0, 97, 45, 67, 97, 0, 0,
  /* 30091 */ 97, 2037, 2038, 97, 97, 45, 45, 45, 45, 67, 67, 67, 67, 1867, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1774,
  /* 30115 */ 97, 97, 97, 97, 97, 97, 0, 94242, 0, 0, 0, 38, 102439, 0, 0, 106538, 98347, 28809, 45, 45, 142, 45, 45,
  /* 30138 */ 45, 1412, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 432, 45, 45, 45, 45, 45, 157, 45, 45, 171, 45,
  /* 30163 */ 45, 45, 182, 45, 45, 45, 45, 200, 45, 45, 45, 1543, 45, 45, 45, 45, 45, 45, 45, 45, 1551, 45, 45, 45, 45,
  /* 30188 */ 1181, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1211, 45, 45, 45, 1214, 45, 45, 45, 67, 209, 67, 67, 67,
  /* 30213 */ 224, 67, 67, 238, 67, 67, 67, 249, 67, 0, 97, 2056, 2057, 0, 2059, 45, 67, 0, 97, 45, 67, 97, 0, 0, 1937,
  /* 30238 */ 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 1741, 45, 45, 45, 45, 45, 45, 67, 67, 67, 267, 67, 67, 67,
  /* 30264 */ 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 97, 289, 97, 97, 97, 304, 97, 97, 318, 97, 97, 97, 329, 97,
  /* 30288 */ 97, 0, 0, 97, 1783, 97, 97, 97, 97, 0, 0, 97, 97, 0, 97, 97, 97, 45, 2026, 45, 45, 45, 45, 67, 2030, 67,
  /* 30314 */ 67, 67, 67, 67, 67, 1041, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1044, 67, 67, 67, 67, 67, 67, 97, 97, 347,
  /* 30339 */ 97, 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 45, 666, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 30365 */ 45, 45, 45, 1420, 45, 57889, 0, 0, 54074, 54074, 550, 0, 97, 97, 97, 97, 97, 97, 97, 97, 840, 67, 1007,
  /* 30388 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 759, 67, 67, 67, 67, 67, 67, 67, 1052, 67, 67, 67,
  /* 30414 */ 67, 67, 67, 67, 67, 67, 67, 1031, 67, 67, 67, 67, 67, 97, 97, 97, 1101, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 30439 */ 97, 97, 97, 97, 592, 97, 97, 97, 1190, 45, 45, 45, 45, 45, 1195, 45, 1197, 45, 45, 45, 45, 1201, 45, 45,
  /* 30463 */ 45, 45, 1952, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 250, 67, 67, 67, 1255, 67, 1257, 67,
  /* 30488 */ 67, 67, 67, 1261, 67, 67, 67, 67, 67, 67, 67, 67, 1685, 67, 67, 67, 67, 67, 67, 67, 0, 24851, 12565, 0, 0,
  /* 30513 */ 0, 0, 28809, 53532, 67, 67, 1267, 67, 67, 67, 67, 67, 67, 1273, 67, 67, 67, 67, 67, 67, 67, 67, 1696, 67,
  /* 30537 */ 67, 67, 67, 67, 67, 67, 0, 0, 0, 0, 0, 0, 2162688, 0, 0, 1281, 67, 67, 67, 67, 1285, 67, 67, 67, 67, 67,
  /* 30563 */ 67, 67, 67, 67, 67, 1070, 67, 67, 67, 67, 67, 1335, 97, 1337, 97, 97, 97, 97, 1341, 97, 97, 97, 97, 97,
  /* 30587 */ 97, 97, 97, 882, 97, 97, 97, 97, 97, 97, 97, 1347, 97, 97, 97, 97, 97, 97, 1353, 97, 97, 97, 97, 97, 97,
  /* 30612 */ 1361, 97, 18, 131427, 0, 638, 0, 0, 0, 0, 362, 0, 0, 365, 29315, 367, 0, 544, 0, 550, 0, 2158592, 2158592,
  /* 30635 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2473984, 2158592, 2158592, 2158592, 2990080,
  /* 30646 */ 2158592, 2158592, 2207744, 2207744, 2482176, 2207744, 2207744, 2207744, 2207744, 2207744, 2207744,
  /* 30657 */ 2207744, 0, 0, 0, 0, 0, 0, 2162688, 0, 53530, 97, 97, 97, 1365, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 30681 */ 97, 97, 608, 97, 97, 97, 45, 45, 1424, 45, 1425, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1058, 67, 67,
  /* 30706 */ 67, 67, 45, 1555, 45, 45, 1557, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 707, 45, 45, 45, 45, 67, 67,
  /* 30731 */ 1570, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 773, 67, 67, 1595, 67, 67, 1597, 67, 67, 67, 67,
  /* 30756 */ 67, 67, 67, 67, 67, 67, 67, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 139, 2158592, 2158592, 2158592, 2404352,
  /* 30778 */ 2412544, 97, 97, 97, 1636, 97, 97, 97, 1639, 97, 97, 1641, 97, 97, 97, 97, 97, 97, 1173, 0, 921, 0, 0, 0,
  /* 30802 */ 0, 0, 0, 45, 67, 67, 67, 1693, 67, 67, 67, 67, 67, 67, 67, 1698, 67, 67, 67, 67, 67, 67, 67, 1773, 67, 97,
  /* 30828 */ 97, 97, 97, 97, 97, 97, 625, 97, 97, 97, 97, 97, 97, 97, 97, 850, 97, 97, 97, 97, 97, 97, 97, 97, 880, 97,
  /* 30854 */ 97, 97, 97, 97, 97, 97, 97, 1106, 97, 97, 97, 97, 97, 97, 97, 1860, 45, 45, 67, 67, 1865, 67, 67, 67, 67,
  /* 30879 */ 1870, 67, 67, 67, 67, 1875, 67, 67, 97, 97, 1880, 97, 97, 0, 0, 0, 97, 97, 1888, 97, 0, 0, 0, 1938, 97,
  /* 30904 */ 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 1854, 45, 45, 45, 45, 45, 45, 45, 1909, 45, 45, 1911, 67, 67, 67,
  /* 30929 */ 67, 67, 67, 67, 67, 67, 67, 1248, 67, 67, 67, 67, 67, 67, 1922, 67, 67, 1924, 97, 97, 97, 97, 97, 0, 0, 0,
  /* 30955 */ 97, 97, 97, 97, 97, 1898, 45, 45, 45, 45, 45, 45, 1904, 45, 45, 67, 67, 67, 67, 97, 97, 97, 97, 0, 0,
  /* 30980 */ 16384, 97, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 1724, 2008, 2009, 45, 45, 67, 67, 67,
  /* 31004 */ 2014, 2015, 67, 67, 97, 97, 0, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 31030 */ 45, 45, 45, 45, 2022, 0, 2023, 97, 97, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 1869, 67, 67, 67,
  /* 31055 */ 67, 67, 67, 0, 94242, 0, 0, 0, 38, 102439, 0, 0, 106538, 98347, 28809, 45, 45, 45, 147, 151, 154, 45, 162,
  /* 31078 */ 45, 45, 176, 178, 181, 45, 45, 45, 192, 196, 45, 45, 45, 45, 2012, 67, 67, 67, 67, 67, 67, 2018, 97, 0, 0,
  /* 31103 */ 97, 1978, 97, 97, 97, 1982, 45, 45, 45, 45, 45, 45, 45, 45, 45, 972, 973, 45, 45, 45, 45, 45, 67, 259,
  /* 31127 */ 263, 67, 67, 67, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 97, 97, 294, 298, 301, 97, 309, 97,
  /* 31150 */ 97, 323, 325, 328, 97, 97, 97, 97, 97, 560, 97, 97, 97, 569, 97, 97, 97, 97, 97, 97, 306, 97, 97, 97, 97,
  /* 31175 */ 97, 97, 97, 97, 97, 1624, 97, 97, 97, 97, 97, 97, 97, 0, 921, 0, 1175, 0, 0, 0, 0, 45, 339, 343, 97, 97,
  /* 31201 */ 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 67, 67, 503, 67, 67, 67, 67, 67, 67, 67, 67, 67, 512, 67,
  /* 31227 */ 67, 519, 97, 97, 600, 97, 97, 97, 97, 97, 97, 97, 97, 97, 609, 97, 97, 616, 45, 649, 45, 45, 45, 45, 45,
  /* 31252 */ 654, 45, 45, 45, 45, 45, 45, 45, 45, 1393, 45, 45, 45, 45, 45, 45, 45, 45, 1209, 45, 45, 45, 45, 45, 45,
  /* 31277 */ 45, 67, 763, 67, 67, 67, 67, 67, 67, 67, 67, 770, 67, 67, 67, 774, 67, 0, 2045, 97, 97, 97, 97, 45, 45,
  /* 31302 */ 67, 67, 0, 0, 97, 97, 45, 45, 45, 994, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 213, 67, 219, 67,
  /* 31328 */ 67, 232, 67, 242, 67, 247, 67, 67, 67, 779, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1018,
  /* 31353 */ 67, 67, 67, 67, 811, 67, 67, 67, 67, 67, 67, 67, 67, 67, 25398, 542, 13112, 544, 57889, 0, 0, 54074,
  /* 31375 */ 54074, 550, 0, 97, 834, 97, 97, 97, 97, 97, 839, 97, 18, 131427, 0, 638, 0, 0, 0, 0, 362, 0, 0, 365,
  /* 31399 */ 29315, 367, 645, 97, 97, 861, 97, 97, 97, 97, 97, 97, 97, 97, 868, 97, 97, 97, 872, 97, 97, 877, 97, 97,
  /* 31423 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 613, 97, 97, 97, 97, 97, 909, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 31449 */ 97, 0, 0, 0, 18, 18, 24, 24, 27, 27, 27, 1036, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 31476 */ 1047, 67, 67, 67, 1050, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1033, 67, 67, 67, 97, 97, 1130,
  /* 31500 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 638, 0, 0, 67, 67, 67, 1295, 67, 67, 67, 0, 0, 0, 0,
  /* 31527 */ 0, 0, 0, 0, 0, 97, 1317, 97, 97, 97, 97, 97, 97, 1375, 97, 97, 97, 0, 0, 0, 45, 1379, 45, 45, 45, 45, 45,
  /* 31554 */ 45, 422, 45, 45, 45, 429, 431, 45, 45, 45, 45, 0, 1090, 0, 0, 97, 1479, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 31579 */ 97, 97, 1357, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1716, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1723, 0, 921,
  /* 31604 */ 29315, 0, 0, 0, 0, 45, 929, 45, 45, 45, 45, 45, 45, 45, 1392, 45, 45, 45, 45, 45, 45, 45, 45, 45, 960, 45,
  /* 31630 */ 45, 45, 45, 45, 45, 97, 97, 97, 1738, 45, 45, 45, 45, 45, 45, 45, 1743, 45, 45, 45, 45, 166, 45, 45, 45,
  /* 31655 */ 45, 184, 186, 45, 45, 197, 45, 45, 97, 1779, 0, 0, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 0, 97, 18,
  /* 31680 */ 131427, 0, 638, 0, 0, 0, 0, 362, 0, 640, 365, 29315, 367, 0, 921, 29315, 0, 0, 0, 0, 45, 45, 45, 45, 45,
  /* 31705 */ 45, 45, 45, 45, 45, 1537, 45, 45, 45, 45, 45, 1803, 45, 45, 45, 45, 45, 1809, 45, 45, 45, 67, 67, 67,
  /* 31729 */ 1814, 67, 67, 67, 67, 67, 67, 1821, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97,
  /* 31755 */ 0, 0, 67, 67, 67, 1818, 67, 67, 67, 67, 67, 1824, 67, 67, 67, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97,
  /* 31782 */ 1890, 0, 1829, 97, 97, 0, 0, 97, 97, 1836, 97, 97, 0, 0, 0, 97, 97, 97, 97, 1981, 45, 45, 45, 45, 45, 45,
  /* 31808 */ 45, 45, 45, 1987, 1845, 97, 97, 97, 45, 45, 45, 45, 45, 1853, 45, 45, 45, 1857, 45, 45, 45, 67, 1864, 67,
  /* 31832 */ 1866, 67, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 97, 97, 1710, 1711, 67, 67, 97, 97, 97, 97,
  /* 31857 */ 97, 0, 0, 0, 1886, 97, 97, 97, 0, 0, 97, 97, 97, 97, 1838, 0, 0, 0, 97, 1843, 97, 0, 1893, 97, 97, 97, 97,
  /* 31884 */ 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1745, 45, 45, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 0, 0,
  /* 31910 */ 1931, 97, 97, 97, 97, 97, 588, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 629, 97, 97, 97, 97, 97, 67, 2044,
  /* 31935 */ 0, 97, 97, 97, 97, 45, 45, 67, 67, 0, 0, 97, 97, 45, 45, 45, 1660, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 31962 */ 45, 45, 453, 45, 455, 67, 67, 67, 67, 268, 67, 67, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 97,
  /* 31986 */ 348, 97, 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 131427, 0, 359, 0, 0, 362, 0, 365, 28809, 367,
  /* 32010 */ 139, 45, 45, 45, 45, 45, 421, 45, 45, 45, 45, 45, 45, 45, 434, 45, 45, 695, 45, 45, 45, 45, 45, 45, 45,
  /* 32035 */ 45, 45, 45, 45, 45, 45, 45, 45, 1667, 45, 0, 921, 29315, 0, 925, 0, 0, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 32061 */ 1811, 45, 67, 67, 67, 67, 67, 67, 1037, 67, 1039, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1277,
  /* 32085 */ 67, 67, 67, 67, 67, 67, 67, 67, 25398, 0, 13112, 0, 54074, 0, 0, 0, 1095, 0, 0, 0, 1096, 97, 97, 97, 97,
  /* 32110 */ 97, 97, 97, 97, 97, 97, 97, 97, 869, 97, 97, 97, 97, 97, 97, 1131, 97, 1133, 97, 97, 97, 97, 97, 97, 97,
  /* 32135 */ 97, 97, 97, 1370, 97, 97, 97, 97, 97, 1312, 0, 0, 0, 0, 1096, 0, 0, 0, 97, 97, 97, 97, 97, 97, 97, 1327,
  /* 32161 */ 97, 97, 97, 97, 97, 1332, 97, 97, 97, 1830, 97, 0, 0, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 1896, 97,
  /* 32187 */ 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1548, 45, 45, 45, 45, 45, 45, 133, 94242, 0, 0, 0, 38, 102439, 0,
  /* 32212 */ 0, 106538, 98347, 28809, 45, 45, 45, 45, 380, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 401, 45, 45, 158,
  /* 32235 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1200, 45, 45, 45, 45, 206, 67, 67, 67, 67, 67, 225,
  /* 32260 */ 67, 67, 67, 67, 67, 67, 67, 67, 754, 67, 67, 67, 67, 67, 67, 67, 57889, 0, 0, 54074, 54074, 550, 832, 97,
  /* 32284 */ 97, 97, 97, 97, 97, 97, 97, 97, 1342, 97, 97, 97, 97, 97, 97, 67, 67, 67, 67, 67, 25398, 1083, 13112,
  /* 32307 */ 1087, 54074, 1091, 0, 0, 0, 0, 0, 0, 1316, 0, 831, 97, 97, 97, 97, 97, 97, 97, 1174, 921, 0, 1175, 0, 0,
  /* 32332 */ 0, 0, 45, 0, 94242, 0, 0, 0, 38, 102439, 0, 0, 106538, 98347, 28809, 45, 45, 45, 148, 67, 67, 264, 67, 67,
  /* 32356 */ 67, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 97, 97, 295, 97, 97, 97, 97, 313, 97, 97, 97, 97,
  /* 32380 */ 331, 333, 97, 18, 131427, 356, 638, 0, 0, 0, 0, 362, 0, 0, 365, 0, 367, 0, 45, 45, 1530, 45, 45, 45, 45,
  /* 32405 */ 45, 45, 45, 45, 45, 45, 45, 45, 988, 45, 45, 45, 97, 344, 97, 97, 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27,
  /* 32431 */ 27, 27, 402, 404, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1756, 67, 438, 45, 45, 45, 45,
  /* 32456 */ 45, 45, 45, 45, 449, 450, 45, 45, 45, 67, 67, 214, 218, 221, 67, 229, 67, 67, 243, 245, 248, 67, 67, 67,
  /* 32480 */ 67, 67, 488, 490, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1071, 67, 1073, 67, 67, 67, 67, 67, 524, 67,
  /* 32505 */ 67, 67, 67, 67, 67, 67, 67, 535, 536, 67, 67, 67, 67, 67, 67, 1683, 1684, 67, 67, 67, 67, 1688, 1689, 67,
  /* 32529 */ 67, 67, 67, 67, 67, 1586, 67, 67, 67, 67, 67, 67, 67, 67, 67, 469, 67, 67, 67, 67, 67, 67, 97, 97, 97,
  /* 32554 */ 585, 587, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1163, 97, 97, 97, 97, 97, 97, 97, 621, 97, 97, 97,
  /* 32579 */ 97, 97, 97, 97, 97, 632, 633, 97, 97, 0, 0, 1782, 97, 97, 97, 97, 97, 0, 0, 97, 97, 0, 97, 712, 45, 45,
  /* 32605 */ 45, 717, 45, 45, 45, 45, 45, 45, 45, 45, 725, 45, 45, 45, 163, 167, 173, 177, 45, 45, 45, 45, 45, 193, 45,
  /* 32630 */ 45, 45, 45, 982, 45, 45, 45, 45, 45, 45, 987, 45, 45, 45, 45, 45, 1558, 45, 1560, 45, 45, 45, 45, 45, 45,
  /* 32655 */ 45, 45, 704, 705, 45, 45, 45, 45, 45, 45, 45, 45, 731, 45, 45, 45, 67, 67, 67, 67, 67, 739, 67, 67, 67,
  /* 32680 */ 67, 67, 67, 273, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 67, 67, 67, 764, 67, 67, 67, 67, 67, 67, 67,
  /* 32704 */ 67, 67, 67, 67, 67, 1290, 67, 67, 67, 67, 67, 67, 812, 67, 67, 67, 67, 818, 67, 67, 67, 25398, 542, 13112,
  /* 32728 */ 544, 57889, 0, 0, 54074, 54074, 550, 0, 97, 97, 97, 97, 97, 837, 97, 97, 97, 97, 97, 602, 97, 97, 97, 97,
  /* 32752 */ 97, 97, 97, 97, 97, 97, 1137, 97, 97, 97, 97, 97, 97, 97, 97, 97, 862, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 32778 */ 97, 97, 1627, 97, 97, 97, 0, 97, 97, 97, 97, 910, 97, 97, 97, 97, 916, 97, 97, 97, 0, 0, 0, 97, 97, 1940,
  /* 32804 */ 97, 97, 1942, 45, 45, 45, 45, 45, 45, 385, 45, 45, 45, 45, 395, 45, 45, 45, 45, 966, 45, 969, 45, 45, 45,
  /* 32829 */ 45, 45, 45, 45, 45, 45, 45, 975, 45, 45, 45, 406, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 974, 45,
  /* 32855 */ 45, 45, 67, 67, 67, 67, 1010, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1262, 67, 67, 67, 67, 67, 67,
  /* 32880 */ 67, 67, 67, 1040, 67, 1042, 67, 1045, 67, 67, 67, 67, 67, 67, 67, 97, 1706, 97, 97, 97, 1709, 97, 97, 97,
  /* 32904 */ 67, 67, 67, 67, 1051, 67, 67, 67, 67, 67, 1057, 67, 67, 67, 67, 67, 67, 67, 1443, 67, 67, 1446, 67, 67,
  /* 32928 */ 67, 67, 67, 67, 67, 1297, 0, 0, 0, 1303, 0, 0, 0, 1309, 67, 67, 67, 67, 1079, 25398, 0, 13112, 0, 54074,
  /* 32952 */ 0, 0, 0, 0, 0, 0, 0, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 32968 */ 2207744, 2207744, 2207744, 2207744, 2207744, 2572288, 2207744, 2207744, 2207744, 1098, 97, 97, 97, 97, 97,
  /* 32983 */ 1104, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1356, 97, 97, 97, 97, 97, 97, 1128, 97, 97, 97, 97, 97, 97,
  /* 33007 */ 1134, 97, 1136, 97, 1139, 97, 97, 97, 97, 97, 97, 1622, 97, 97, 97, 97, 97, 97, 97, 97, 0, 921, 0, 0, 0,
  /* 33032 */ 1176, 0, 646, 45, 67, 67, 67, 1268, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1469, 67, 67, 67, 97,
  /* 33057 */ 1348, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1127, 97, 67, 1569, 67, 67, 67, 67, 67, 67,
  /* 33082 */ 67, 67, 67, 67, 67, 67, 67, 67, 1448, 1449, 67, 1816, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1825, 67, 67,
  /* 33106 */ 1827, 97, 97, 0, 1781, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 0, 97, 97, 97, 1831, 0, 0, 97, 97, 97, 97,
  /* 33132 */ 97, 0, 0, 0, 97, 97, 97, 1980, 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1395, 45, 45, 45, 45, 45, 97,
  /* 33158 */ 1846, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1212, 45, 45, 45, 45, 45, 45, 2010, 45, 67,
  /* 33183 */ 67, 67, 67, 67, 2016, 67, 97, 97, 0, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 45, 45, 2007, 0, 94242, 0, 0,
  /* 33209 */ 0, 38, 102439, 0, 0, 106538, 98347, 28809, 45, 45, 143, 45, 45, 45, 1671, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 33232 */ 45, 45, 45, 67, 1813, 67, 67, 1815, 45, 45, 67, 210, 67, 67, 67, 67, 67, 67, 239, 67, 67, 67, 67, 67, 67,
  /* 33257 */ 67, 1454, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1445, 67, 67, 67, 67, 67, 67, 97, 97, 290, 97, 97, 97, 97,
  /* 33282 */ 97, 97, 319, 97, 97, 97, 97, 97, 97, 303, 97, 97, 317, 97, 97, 97, 97, 97, 97, 305, 97, 97, 97, 97, 97,
  /* 33307 */ 97, 97, 97, 97, 899, 97, 97, 97, 97, 97, 97, 375, 45, 45, 45, 379, 45, 45, 390, 45, 45, 394, 45, 45, 45,
  /* 33332 */ 45, 45, 443, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 461, 67, 67, 67, 465, 67, 67, 476, 67,
  /* 33357 */ 67, 480, 67, 67, 67, 67, 67, 67, 1694, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1288, 67, 67, 67, 67, 67, 67,
  /* 33382 */ 500, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1075, 97, 97, 97, 558, 97, 97, 97, 562,
  /* 33407 */ 97, 97, 573, 97, 97, 577, 97, 97, 97, 97, 97, 895, 97, 97, 97, 97, 97, 97, 903, 97, 97, 97, 0, 97, 97,
  /* 33432 */ 1638, 97, 97, 97, 97, 97, 97, 97, 97, 1646, 597, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 33457 */ 97, 1334, 45, 681, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1396, 45, 45, 1399, 45, 45,
  /* 33481 */ 730, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1434, 67, 67, 67, 67, 67, 67, 750, 67, 67,
  /* 33506 */ 67, 67, 67, 67, 67, 67, 67, 67, 1456, 67, 67, 67, 67, 67, 45, 45, 993, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 33532 */ 45, 45, 67, 67, 1238, 67, 67, 1006, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1280,
  /* 33556 */ 1048, 1049, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1059, 67, 67, 67, 67, 67, 67, 1286, 67, 67, 67, 67,
  /* 33580 */ 67, 67, 67, 1291, 67, 97, 97, 1100, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 638, 0, 920, 97,
  /* 33605 */ 97, 1142, 1143, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1153, 97, 97, 97, 97, 97, 1158, 97, 97, 97, 1161,
  /* 33629 */ 97, 97, 97, 97, 1166, 97, 97, 97, 97, 97, 1325, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1328, 97, 97, 97,
  /* 33654 */ 97, 97, 97, 97, 45, 1218, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1678, 45, 45, 45, 67,
  /* 33679 */ 67, 67, 67, 67, 1269, 67, 67, 67, 67, 67, 67, 67, 67, 1278, 67, 67, 67, 67, 67, 67, 1761, 67, 67, 67, 67,
  /* 33704 */ 67, 67, 67, 67, 67, 530, 67, 67, 67, 67, 67, 67, 97, 97, 1349, 97, 97, 97, 97, 97, 97, 97, 97, 1358, 97,
  /* 33729 */ 97, 97, 97, 97, 97, 1623, 97, 97, 97, 97, 97, 97, 97, 97, 0, 921, 0, 0, 926, 0, 0, 0, 45, 45, 1411, 45,
  /* 33755 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1754, 45, 45, 67, 67, 1301, 0, 1307, 0, 1313, 97, 97,
  /* 33780 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 21054, 97, 97, 97, 97, 67, 1757, 67, 67, 67, 1760, 67, 67, 67, 67, 67,
  /* 33805 */ 67, 67, 67, 67, 67, 1467, 67, 67, 67, 67, 67, 1778, 97, 0, 0, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 0, 97,
  /* 33832 */ 97, 97, 97, 97, 1352, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1511, 97, 97, 97, 97, 97, 67, 67, 67, 67,
  /* 33857 */ 67, 1820, 67, 1822, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 0, 0, 0, 97, 1933, 97, 1892, 97, 97, 97, 97,
  /* 33882 */ 97, 97, 1899, 45, 45, 45, 45, 45, 45, 45, 45, 1664, 45, 45, 45, 45, 45, 45, 45, 45, 1546, 45, 45, 45, 45,
  /* 33907 */ 45, 45, 45, 45, 1208, 45, 45, 45, 45, 45, 45, 45, 45, 1224, 45, 45, 45, 45, 45, 45, 45, 45, 673, 45, 45,
  /* 33932 */ 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 1925, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 97, 623, 97, 97,
  /* 33958 */ 97, 97, 97, 97, 97, 97, 97, 97, 307, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1796, 97, 45, 45, 45, 45, 45, 45,
  /* 33984 */ 45, 970, 45, 45, 45, 45, 45, 45, 45, 45, 1417, 45, 45, 45, 45, 45, 45, 45, 67, 1964, 67, 67, 97, 97, 97,
  /* 34009 */ 97, 0, 0, 0, 97, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 1721, 97, 97, 0, 0, 1997, 97, 0, 0, 2000, 97, 97,
  /* 34036 */ 0, 97, 97, 97, 97, 97, 45, 45, 45, 45, 733, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 803, 67, 67, 67,
  /* 34062 */ 67, 67, 0, 94242, 0, 0, 0, 38, 102439, 0, 0, 106538, 98347, 28809, 45, 45, 144, 45, 45, 45, 1805, 45,
  /* 34084 */ 1807, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 231, 67, 67, 67, 67, 67, 67, 67, 0, 24850, 12564, 0, 0,
  /* 34109 */ 0, 0, 28809, 53531, 45, 45, 67, 211, 67, 67, 67, 67, 230, 234, 240, 244, 67, 67, 67, 67, 67, 67, 464, 67,
  /* 34133 */ 67, 67, 67, 67, 67, 479, 67, 67, 67, 260, 67, 67, 67, 67, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531,
  /* 34157 */ 97, 97, 291, 97, 97, 97, 97, 310, 314, 320, 324, 97, 97, 97, 97, 97, 97, 1367, 97, 97, 97, 97, 97, 97, 97,
  /* 34182 */ 97, 97, 1355, 97, 97, 97, 97, 97, 97, 1362, 340, 97, 97, 97, 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27,
  /* 34207 */ 27, 131427, 0, 0, 360, 0, 362, 0, 365, 28809, 367, 139, 369, 45, 45, 45, 374, 67, 67, 460, 67, 67, 67, 67,
  /* 34231 */ 466, 67, 67, 67, 67, 67, 67, 67, 67, 801, 67, 67, 67, 67, 67, 67, 67, 67, 67, 487, 67, 67, 67, 67, 67, 67,
  /* 34257 */ 67, 67, 67, 67, 498, 67, 67, 67, 67, 67, 67, 1772, 67, 67, 97, 97, 97, 97, 97, 97, 97, 0, 921, 922, 1175,
  /* 34282 */ 0, 0, 0, 0, 45, 67, 502, 67, 67, 67, 67, 67, 67, 67, 508, 67, 67, 67, 515, 517, 67, 67, 67, 67, 67, 97,
  /* 34308 */ 97, 97, 97, 97, 0, 0, 0, 1932, 97, 97, 0, 1999, 97, 97, 97, 0, 97, 97, 2004, 2005, 97, 45, 45, 45, 45,
  /* 34333 */ 1193, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 676, 45, 45, 45, 45, 67, 24850, 24850, 12564, 12564, 0,
  /* 34356 */ 57889, 0, 0, 0, 53531, 53531, 367, 286, 552, 97, 97, 97, 97, 97, 1377, 0, 0, 45, 45, 45, 45, 45, 45, 45,
  /* 34380 */ 45, 655, 45, 45, 45, 45, 45, 45, 45, 97, 97, 557, 97, 97, 97, 97, 563, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 34405 */ 1135, 97, 97, 97, 97, 97, 97, 97, 97, 97, 584, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 595, 97, 97, 97,
  /* 34430 */ 97, 97, 911, 97, 97, 97, 97, 97, 97, 97, 638, 0, 0, 0, 0, 1315, 0, 0, 0, 0, 97, 97, 97, 1319, 97, 97, 97,
  /* 34457 */ 0, 97, 97, 97, 97, 97, 97, 1733, 97, 97, 97, 97, 97, 97, 1340, 97, 97, 97, 1343, 97, 97, 1345, 97, 1346,
  /* 34481 */ 97, 599, 97, 97, 97, 97, 97, 97, 97, 605, 97, 97, 97, 612, 614, 97, 97, 97, 97, 97, 1794, 97, 97, 97, 45,
  /* 34506 */ 45, 45, 45, 45, 45, 45, 1207, 45, 45, 45, 45, 45, 45, 1213, 45, 45, 745, 67, 67, 67, 67, 751, 67, 67, 67,
  /* 34531 */ 67, 67, 67, 67, 67, 67, 67, 1577, 67, 67, 67, 67, 67, 762, 67, 67, 67, 67, 766, 67, 67, 67, 67, 67, 67,
  /* 34556 */ 67, 67, 67, 67, 1765, 67, 67, 67, 67, 67, 777, 67, 67, 781, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 34581 */ 67, 1592, 1593, 67, 67, 97, 843, 97, 97, 97, 97, 849, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1510, 97, 97,
  /* 34605 */ 97, 97, 97, 97, 97, 860, 97, 97, 97, 97, 864, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1797, 45, 45, 45, 45,
  /* 34630 */ 1801, 45, 97, 875, 97, 97, 879, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1522, 97, 97, 97, 97, 97, 991,
  /* 34655 */ 45, 45, 45, 45, 996, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 215, 67, 67, 67, 67, 233, 67, 67, 67, 67,
  /* 34680 */ 251, 253, 1022, 67, 67, 67, 1026, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1035, 67, 67, 1038, 67, 67, 67,
  /* 34704 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1458, 67, 67, 67, 67, 67, 1064, 67, 67, 67, 1067, 67, 67, 67, 67,
  /* 34729 */ 1072, 67, 67, 67, 67, 67, 67, 1296, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2367488, 2158592, 2158592, 2158592,
  /* 34750 */ 2158592, 2158592, 2158592, 67, 67, 67, 67, 67, 25398, 0, 13112, 0, 54074, 0, 0, 0, 0, 1096, 0, 921, 29315,
  /* 34771 */ 0, 0, 0, 0, 928, 45, 45, 45, 45, 45, 934, 45, 45, 45, 164, 45, 45, 45, 45, 45, 45, 45, 45, 45, 198, 45,
  /* 34797 */ 45, 45, 378, 45, 45, 45, 45, 45, 45, 393, 45, 45, 45, 398, 45, 97, 97, 1116, 97, 97, 97, 1120, 97, 97, 97,
  /* 34822 */ 97, 97, 97, 97, 97, 97, 1147, 1148, 97, 97, 97, 97, 97, 97, 97, 1129, 97, 97, 1132, 97, 97, 97, 97, 97,
  /* 34846 */ 97, 97, 97, 97, 97, 97, 1626, 97, 97, 97, 97, 0, 45, 1178, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1185, 45,
  /* 34871 */ 45, 45, 45, 441, 45, 45, 45, 45, 45, 45, 451, 45, 45, 67, 67, 67, 67, 67, 227, 67, 67, 67, 67, 67, 67, 67,
  /* 34897 */ 67, 1260, 67, 67, 67, 1263, 67, 67, 1265, 1203, 45, 45, 1205, 45, 1206, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 34920 */ 45, 1216, 67, 1266, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1276, 67, 67, 67, 67, 67, 67, 492, 67, 67, 67, 67,
  /* 34945 */ 67, 67, 67, 67, 67, 471, 67, 67, 67, 67, 481, 67, 45, 1386, 45, 1389, 45, 45, 45, 45, 1394, 45, 45, 45,
  /* 34969 */ 1397, 45, 45, 45, 45, 995, 45, 997, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 1915, 67, 67, 67, 67, 67,
  /* 34994 */ 1422, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1433, 67, 1436, 67, 67, 67, 67, 1441, 67, 67, 67,
  /* 35018 */ 1444, 67, 67, 67, 67, 67, 67, 67, 0, 24850, 12564, 0, 0, 0, 281, 28809, 53531, 97, 97, 97, 97, 1494, 97,
  /* 35041 */ 97, 97, 1497, 97, 97, 97, 97, 97, 97, 97, 1368, 97, 97, 97, 97, 97, 97, 97, 97, 851, 97, 97, 97, 97, 97,
  /* 35066 */ 97, 97, 67, 67, 67, 1571, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 25398, 542, 13112, 544, 67, 67,
  /* 35090 */ 1583, 67, 67, 67, 67, 67, 67, 67, 67, 1591, 67, 67, 67, 67, 67, 67, 752, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 35115 */ 67, 1056, 67, 67, 67, 67, 67, 67, 97, 1634, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1125,
  /* 35140 */ 97, 97, 97, 1647, 97, 97, 97, 97, 97, 0, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1183, 45, 45, 45, 45, 45, 45,
  /* 35166 */ 45, 45, 45, 409, 45, 45, 45, 45, 45, 45, 1658, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 35191 */ 1668, 1712, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0, 1835, 97, 97, 97, 97, 0, 0, 0, 97,
  /* 35217 */ 97, 1844, 97, 97, 1726, 0, 97, 97, 97, 97, 97, 1732, 97, 1734, 97, 97, 97, 97, 97, 300, 97, 308, 97, 97,
  /* 35241 */ 97, 97, 97, 97, 97, 97, 866, 97, 97, 97, 97, 97, 97, 97, 67, 67, 67, 1758, 67, 67, 67, 1762, 67, 67, 67,
  /* 35266 */ 67, 67, 67, 67, 67, 1043, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1771, 67, 67, 67, 97, 97, 97,
  /* 35291 */ 97, 97, 1776, 97, 97, 97, 97, 297, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1108, 97, 97, 97, 97, 67,
  /* 35316 */ 67, 67, 1966, 97, 97, 97, 1970, 0, 0, 0, 97, 97, 97, 97, 0, 97, 97, 97, 1720, 97, 97, 97, 97, 97, 0, 0,
  /* 35342 */ 97, 97, 97, 1837, 97, 0, 1840, 1841, 97, 97, 97, 1988, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1994, 1995,
  /* 35366 */ 67, 97, 97, 97, 97, 97, 1103, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 917, 97, 97, 0, 0, 0, 67, 67, 265,
  /* 35392 */ 67, 67, 67, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 345, 97, 97, 97, 97, 0, 40976, 0, 18, 18,
  /* 35416 */ 24, 24, 27, 27, 27, 131427, 0, 0, 0, 361, 362, 0, 365, 28809, 367, 139, 45, 45, 45, 45, 45, 671, 45, 45,
  /* 35440 */ 45, 45, 45, 45, 45, 45, 45, 45, 411, 45, 45, 414, 45, 45, 45, 45, 377, 45, 45, 45, 386, 45, 45, 45, 45,
  /* 35465 */ 45, 45, 45, 45, 45, 1223, 45, 45, 45, 45, 45, 45, 45, 45, 45, 426, 45, 45, 433, 45, 45, 45, 67, 67, 67,
  /* 35490 */ 67, 67, 463, 67, 67, 67, 472, 67, 67, 67, 67, 67, 67, 67, 527, 67, 67, 67, 67, 67, 67, 537, 67, 540,
  /* 35514 */ 24850, 24850, 12564, 12564, 0, 57889, 0, 0, 0, 53531, 53531, 367, 286, 97, 97, 97, 97, 97, 1119, 97, 97,
  /* 35535 */ 97, 97, 97, 97, 97, 97, 97, 97, 1509, 97, 97, 97, 97, 97, 97, 97, 97, 564, 97, 97, 97, 97, 97, 97, 97,
  /* 35560 */ 637, 18, 131427, 0, 0, 0, 0, 0, 0, 362, 0, 0, 365, 29315, 367, 0, 921, 29315, 0, 0, 0, 927, 45, 45, 45,
  /* 35585 */ 45, 45, 45, 45, 45, 45, 1234, 45, 45, 45, 45, 67, 67, 67, 67, 1240, 45, 697, 45, 45, 45, 45, 45, 45, 45,
  /* 35610 */ 45, 45, 45, 708, 45, 45, 45, 45, 1221, 45, 45, 45, 45, 1225, 45, 45, 45, 45, 45, 45, 384, 45, 45, 45, 45,
  /* 35635 */ 45, 45, 45, 45, 45, 1210, 45, 45, 45, 45, 45, 45, 67, 67, 795, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 35661 */ 67, 67, 1470, 67, 67, 67, 67, 67, 67, 67, 815, 67, 67, 67, 67, 67, 67, 25398, 542, 13112, 544, 97, 97, 97,
  /* 35685 */ 893, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1164, 97, 97, 97, 67, 67, 67, 1025, 67, 67, 67, 67,
  /* 35710 */ 67, 67, 67, 67, 67, 67, 67, 67, 1687, 67, 67, 67, 67, 67, 67, 67, 67, 67, 25398, 0, 13112, 0, 54074, 0, 0,
  /* 35735 */ 0, 0, 0, 1097, 1241, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1450, 45, 45, 1388, 45,
  /* 35760 */ 1390, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1236, 67, 67, 67, 67, 67, 1437, 67, 67, 67, 67, 67, 67,
  /* 35785 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 1472, 1490, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 35810 */ 97, 1503, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 0, 1930, 0, 97, 97, 97, 97, 97, 847, 97, 97, 97, 97, 97,
  /* 35836 */ 97, 97, 97, 97, 858, 67, 67, 1965, 67, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 0, 97, 97, 1719, 97, 97,
  /* 35862 */ 97, 97, 97, 97, 0, 0, 0, 45, 45, 45, 45, 1382, 45, 1383, 45, 45, 45, 159, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 35888 */ 45, 45, 45, 45, 45, 1563, 45, 45, 45, 45, 45, 67, 261, 67, 67, 67, 67, 67, 0, 24850, 12564, 0, 0, 0, 0,
  /* 35913 */ 28809, 53531, 341, 97, 97, 97, 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 97, 1099, 97, 97, 97, 97,
  /* 35937 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1333, 97, 1230, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67,
  /* 35962 */ 67, 67, 67, 67, 1992, 67, 1993, 67, 67, 67, 97, 97, 45, 45, 160, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 35987 */ 45, 45, 45, 1665, 45, 45, 45, 45, 45, 131427, 357, 0, 0, 0, 362, 0, 365, 28809, 367, 139, 45, 45, 45, 45,
  /* 36011 */ 45, 684, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 412, 45, 45, 45, 416, 45, 45, 45, 440, 45, 45, 45, 45,
  /* 36036 */ 45, 45, 45, 45, 45, 45, 45, 67, 67, 1990, 67, 1991, 67, 67, 67, 67, 67, 67, 67, 97, 97, 1707, 97, 97, 97,
  /* 36061 */ 97, 97, 97, 501, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1691, 67, 67, 67, 67, 67,
  /* 36086 */ 526, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1030, 67, 1032, 67, 67, 67, 67, 598, 97, 97, 97, 97, 97, 97,
  /* 36111 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 1632, 0, 921, 29315, 923, 0, 0, 0, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 36137 */ 1404, 45, 45, 45, 45, 45, 45, 45, 45, 45, 425, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 25398, 0,
  /* 36161 */ 13112, 0, 54074, 0, 0, 1093, 0, 0, 0, 0, 0, 97, 1609, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1369, 97, 97,
  /* 36186 */ 97, 1372, 97, 97, 67, 67, 266, 67, 67, 67, 67, 0, 24850, 12564, 0, 0, 0, 0, 28809, 53531, 97, 346, 97, 97,
  /* 36210 */ 97, 97, 0, 40976, 0, 18, 18, 24, 24, 27, 27, 27, 665, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 36236 */ 45, 45, 1677, 45, 45, 45, 45, 67, 45, 45, 954, 45, 956, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1545,
  /* 36261 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 448, 45, 45, 45, 45, 67, 456, 67, 67, 67, 67, 67, 1270, 67, 67, 67,
  /* 36286 */ 67, 67, 67, 67, 67, 67, 67, 1069, 67, 67, 67, 67, 67, 67, 97, 97, 97, 1350, 97, 97, 97, 97, 97, 97, 97,
  /* 36311 */ 97, 97, 97, 97, 97, 1524, 97, 97, 97, 97, 97, 97, 97, 1376, 0, 0, 0, 45, 45, 45, 45, 45, 45, 45, 45, 1559,
  /* 36337 */ 1561, 45, 45, 45, 1564, 45, 1566, 1567, 45, 67, 67, 67, 67, 67, 1573, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 36361 */ 67, 1247, 67, 67, 67, 67, 67, 1252, 97, 1725, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1628,
  /* 36386 */ 97, 1630, 0, 0, 94242, 0, 0, 0, 2211840, 0, 1118208, 0, 0, 0, 0, 2158592, 2158731, 2158592, 2158592,
  /* 36405 */ 2158592, 3117056, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 36416 */ 2158592, 2158592, 2158592, 3018752, 2158592, 3043328, 2158592, 2158592, 2158592, 2158592, 3080192,
  /* 36427 */ 2158592, 2158592, 3112960, 2158592, 2158592, 2158592, 2158592, 2158592, 2158878, 2158592, 2158592,
  /* 36438 */ 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 36449 */ 2158592, 2605056, 2158592, 2158592, 2207744, 0, 542, 0, 544, 0, 0, 2166784, 0, 0, 0, 550, 0, 0, 2158592,
  /* 36468 */ 2158592, 2686976, 2158592, 2715648, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592,
  /* 36479 */ 2867200, 2158592, 2904064, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 0, 94242, 0, 0,
  /* 36493 */ 0, 2211840, 0, 0, 1130496, 0, 0, 0, 2158592, 2158592, 2158592, 2158592, 2158592, 3186688, 2158592, 0, 0,
  /* 36510 */ 139, 0, 0, 0, 139, 0, 2367488, 2207744, 0, 0, 0, 0, 176128, 0, 2166784, 0, 0, 0, 0, 0, 286, 2158592,
  /* 36532 */ 2158592, 3170304, 3174400, 2158592, 0, 0, 0, 2158592, 2158592, 2158592, 2158592, 2158592, 2424832,
  /* 36545 */ 2158592, 2158592, 2158592, 1508, 2158592, 2908160, 2158592, 2158592, 2158592, 2977792, 2158592, 2158592,
  /* 36557 */ 2158592, 2158592, 3039232, 2158592, 2158592, 2158592, 2158592, 2158592, 2158592, 3158016, 67, 24850,
  /* 36569 */ 24850, 12564, 12564, 0, 0, 0, 0, 0, 53531, 53531, 0, 286, 97, 97, 97, 97, 97, 1144, 97, 97, 97, 97, 97,
  /* 36592 */ 97, 97, 97, 97, 97, 1149, 97, 97, 97, 97, 1154, 57889, 0, 0, 0, 0, 550, 0, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 36618 */ 97, 561, 97, 97, 97, 97, 97, 97, 576, 97, 97, 139264, 139264, 139264, 139264, 139264, 139264, 139264,
  /* 36636 */ 139264, 139264, 139264, 139264, 139264, 0, 0, 139264, 0, 921, 29315, 0, 0, 926, 0, 45, 45, 45, 45, 45, 45,
  /* 36657 */ 45, 45, 45, 719, 720, 45, 45, 45, 45, 45, 45, 45, 45, 685, 45, 45, 45, 45, 45, 45, 45, 45, 45, 942, 45,
  /* 36682 */ 45, 946, 45, 45, 45, 950, 45, 45, 0, 2146304, 2146304, 0, 0, 0, 0, 2224128, 2224128, 2224128, 2232320,
  /* 36701 */ 2232320, 2232320, 2232320, 0, 0, 1301, 0, 0, 0, 0, 0, 1307, 0, 0, 0, 0, 0, 1313, 0, 0, 0, 0, 0, 0, 0, 97,
  /* 36727 */ 97, 1318, 97, 97, 97, 97, 97, 97, 1795, 97, 97, 45, 45, 45, 45, 45, 45, 45, 446, 45, 45, 45, 45, 45, 45,
  /* 36752 */ 67, 67, 2158592, 2146304, 0, 0, 0, 0, 0, 0, 0, 2211840, 0, 0, 0, 0, 2158592, 0, 921, 29315, 0, 924, 0, 0,
  /* 36776 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 1000, 45, 45, 45, 45, 67, 67
];

XQueryTokenizer.EXPECTED =
[
  /*    0 */ 290, 300, 304, 353, 296, 309, 305, 319, 315, 324, 328, 352, 354, 334, 338, 330, 320, 345, 349, 293, 358,
  /*   21 */ 362, 341, 366, 312, 370, 374, 378, 382, 386, 390, 394, 398, 737, 402, 634, 439, 604, 634, 634, 634, 634,
  /*   42 */ 408, 634, 634, 634, 404, 634, 634, 634, 457, 634, 634, 963, 634, 634, 413, 634, 634, 634, 634, 634, 634,
  /*   63 */ 634, 663, 418, 422, 903, 902, 426, 431, 548, 634, 437, 521, 919, 443, 615, 409, 449, 455, 624, 731, 751,
  /*   84 */ 634, 461, 465, 672, 470, 469, 474, 481, 485, 477, 489, 493, 629, 542, 497, 505, 603, 602, 991, 648, 510,
  /*  105 */ 804, 634, 515, 958, 526, 525, 530, 768, 634, 546, 552, 711, 710, 593, 558, 562, 618, 566, 570, 574, 578,
  /*  126 */ 582, 586, 590, 608, 612, 660, 822, 821, 634, 622, 596, 444, 628, 533, 724, 633, 640, 653, 647, 652, 536,
  /*  147 */ 1008, 451, 450, 445, 657, 670, 676, 685, 689, 693, 697, 701, 704, 707, 715, 719, 798, 815, 634, 723, 762,
  /*  168 */ 996, 634, 728, 969, 730, 735, 908, 634, 741, 679, 889, 511, 747, 634, 750, 755, 499, 666, 499, 501, 759,
  /*  189 */ 772, 776, 780, 634, 787, 784, 797, 802, 809, 808, 427, 814, 1006, 517, 634, 519, 853, 634, 813, 850, 793,
  /*  210 */ 634, 819, 826, 833, 832, 837, 843, 847, 857, 861, 863, 867, 871, 875, 879, 883, 643, 887, 539, 980, 979,
  /*  231 */ 634, 893, 944, 634, 900, 896, 634, 907, 933, 506, 912, 917, 828, 433, 636, 635, 554, 961, 923, 930, 927,
  /*  252 */ 937, 941, 634, 634, 634, 974, 948, 952, 985, 913, 968, 967, 743, 634, 973, 839, 634, 978, 599, 634, 984,
  /*  273 */ 989, 765, 444, 995, 1000, 634, 1003, 790, 955, 1012, 681, 634, 634, 634, 634, 634, 414, 1016, 1020, 1024,
  /*  293 */ 1085, 1027, 1090, 1090, 1046, 1080, 1137, 1108, 1215, 1049, 1032, 1039, 1085, 1085, 1085, 1085, 1058, 1062,
  /*  311 */ 1068, 1085, 1086, 1090, 1090, 1091, 1072, 1064, 1107, 1090, 1090, 1090, 1118, 1123, 1138, 1078, 1074, 1084,
  /*  329 */ 1085, 1085, 1085, 1087, 1090, 1062, 1052, 1060, 1114, 1062, 1104, 1085, 1085, 1090, 1090, 1028, 1122, 1063,
  /*  347 */ 1128, 1139, 1127, 1158, 1085, 1085, 1151, 1090, 1090, 1090, 1095, 1090, 1132, 1073, 1136, 1143, 1061, 1150,
  /*  365 */ 1085, 1155, 1098, 1101, 1146, 1162, 1169, 1101, 1185, 1151, 1090, 1110, 1173, 1054, 1087, 1109, 1177, 1165,
  /*  383 */ 1089, 1204, 1184, 1107, 1189, 1193, 1088, 1197, 1180, 1201, 1208, 1042, 1212, 1219, 1223, 1227, 1231, 1235,
  /*  401 */ 1245, 1777, 1527, 1686, 1686, 1238, 1686, 1254, 1686, 1686, 1686, 1294, 1669, 1686, 1686, 1686, 1322, 1625,
  /*  419 */ 1534, 1268, 1624, 1275, 1281, 1443, 1292, 1300, 1686, 1686, 1686, 1350, 1826, 1306, 1686, 1686, 1240, 2032,
  /*  437 */ 1317, 1321, 1686, 1686, 1253, 1686, 1326, 1686, 1686, 1686, 1418, 1709, 1446, 1686, 1686, 1686, 1492, 1686,
  /*  455 */ 1295, 1447, 1686, 1686, 1258, 1686, 1736, 1686, 1686, 1520, 1355, 1686, 1288, 1348, 1361, 1686, 1359, 1686,
  /*  473 */ 1364, 1498, 1368, 1302, 1362, 1381, 1389, 1395, 1486, 1686, 1371, 1377, 1370, 1686, 1375, 1382, 1384, 1402,
  /*  491 */ 1408, 1385, 1383, 1619, 1413, 1423, 1428, 1433, 1686, 1686, 1270, 1686, 1338, 1686, 1440, 1686, 1686, 1686,
  /*  509 */ 1499, 1465, 1686, 1686, 1686, 1639, 1473, 1884, 1686, 1686, 1293, 1864, 1686, 1686, 1296, 1321, 1483, 1686,
  /*  527 */ 1686, 1686, 1646, 1686, 1748, 1496, 1686, 1418, 1675, 1686, 1418, 1702, 1686, 1418, 1981, 1686, 1429, 1409,
  /*  545 */ 1427, 1504, 1692, 1686, 1686, 1313, 1448, 1651, 1508, 1686, 1686, 1340, 1686, 1903, 1686, 1686, 1435, 1513,
  /*  563 */ 1686, 1283, 1287, 1519, 1686, 1524, 1363, 1568, 1938, 1539, 1566, 1579, 1479, 1533, 1538, 1553, 1544, 1552,
  /*  581 */ 1557, 1563, 1574, 1557, 1583, 1589, 1590, 1759, 1594, 1603, 1607, 1611, 1686, 1436, 1514, 1686, 1434, 1656,
  /*  599 */ 1686, 1434, 1680, 1686, 1453, 1686, 1686, 1686, 1559, 1617, 1686, 1770, 1418, 1623, 1769, 1629, 1686, 1515,
  /*  617 */ 1335, 1686, 1285, 1686, 1671, 1921, 1650, 1686, 1686, 1344, 1308, 1666, 1686, 1686, 1686, 1659, 1685, 1686,
  /*  635 */ 1686, 1686, 1686, 1241, 1686, 1686, 1844, 1691, 1686, 1630, 1977, 1970, 1362, 1686, 1686, 1686, 1693, 1698,
  /*  653 */ 1686, 1686, 1686, 1697, 1686, 1764, 1715, 1686, 1634, 1638, 1686, 1599, 1585, 1686, 1271, 1686, 1269, 1686,
  /*  671 */ 1721, 1686, 1686, 1354, 1686, 1801, 1686, 1799, 1686, 1640, 1686, 1686, 1461, 1686, 1686, 1732, 1686, 1944,
  /*  689 */ 1686, 1740, 1686, 1746, 1415, 1396, 1686, 1598, 1547, 1417, 1597, 1416, 1577, 1546, 1397, 1577, 1547, 1548,
  /*  707 */ 1570, 1398, 1753, 1686, 1652, 1509, 1686, 1686, 1686, 1757, 1686, 1419, 1686, 1763, 1418, 1768, 1781, 1686,
  /*  725 */ 1686, 1686, 1705, 1686, 2048, 1792, 1686, 1686, 1686, 1735, 1686, 1797, 1686, 1686, 1404, 1686, 1639, 1815,
  /*  743 */ 1686, 1686, 1418, 2017, 1820, 1686, 1686, 1803, 1686, 1686, 1686, 1736, 1489, 1686, 1686, 1825, 1338, 1260,
  /*  761 */ 1263, 1686, 1686, 1785, 1686, 1686, 1728, 1686, 1686, 1749, 1497, 1830, 1830, 1262, 1248, 1261, 1329, 1260,
  /*  779 */ 1264, 1329, 1248, 1249, 1259, 1540, 1849, 1842, 1686, 1686, 1835, 1686, 1686, 1816, 1686, 1686, 1831, 1882,
  /*  797 */ 1848, 1686, 1686, 1686, 1774, 2071, 1854, 1686, 1686, 1469, 1884, 1686, 1821, 1859, 1686, 1686, 1350, 1883,
  /*  815 */ 1686, 1686, 1686, 1781, 1391, 1875, 1686, 1686, 1613, 1644, 1686, 1686, 1889, 1686, 1686, 1662, 1884, 1686,
  /*  833 */ 1885, 1890, 1686, 1686, 1686, 1894, 1686, 1686, 1678, 1686, 1907, 1686, 1686, 1529, 1914, 1686, 1838, 1686,
  /*  851 */ 1686, 1881, 1686, 1686, 1872, 1876, 1836, 1919, 1686, 1837, 1692, 1910, 1686, 1925, 1928, 1742, 1686, 1811,
  /*  869 */ 1811, 1930, 1810, 1929, 1935, 1928, 1900, 1942, 1867, 1868, 1931, 1035, 1788, 1948, 1952, 1956, 1960, 1964,
  /*  887 */ 1686, 1976, 1686, 1686, 1686, 2065, 1686, 1992, 2037, 1686, 1686, 1998, 2009, 1972, 2002, 1686, 1686, 1686,
  /*  905 */ 2077, 1300, 2023, 1686, 1686, 1686, 1807, 2031, 1686, 1686, 1686, 1860, 1500, 2032, 1686, 1686, 1686, 2083,
  /*  923 */ 1686, 2036, 1686, 1277, 1276, 2042, 1877, 1686, 1686, 2041, 1686, 1686, 2027, 2037, 2012, 1686, 2012, 1855,
  /*  941 */ 1850, 1686, 2046, 1686, 1686, 2054, 1996, 1686, 1897, 1309, 2059, 2052, 1686, 2058, 1686, 1686, 2081, 1686,
  /*  959 */ 1717, 1477, 1686, 1331, 1686, 1686, 1687, 1686, 1860, 1681, 1686, 1686, 1686, 1966, 1724, 1686, 1686, 1686,
  /*  977 */ 1984, 2015, 1686, 1686, 1686, 1988, 1686, 2063, 1686, 1686, 1686, 2005, 1686, 1727, 1686, 1686, 1711, 1457,
  /*  995 */ 2069, 1686, 1686, 1686, 2019, 2075, 1686, 1686, 1915, 1686, 1686, 1793, 1874, 1686, 1686, 1491, 1362, 1449,
  /* 1013 */ 1686, 1686, 1460, 2098, 2087, 2091, 2095, 2184, 2102, 2113, 2780, 2117, 2134, 2142, 2281, 2146, 2146, 2146,
  /* 1031 */ 2304, 2296, 2181, 2639, 2591, 2872, 2592, 2873, 2313, 2195, 2200, 2281, 2146, 2273, 2226, 2204, 2152, 2219,
  /* 1049 */ 2276, 2167, 2177, 2276, 2235, 2276, 2276, 2230, 2281, 2276, 2296, 2276, 2293, 2276, 2276, 2276, 2276, 2234,
  /* 1067 */ 2276, 2311, 2314, 2210, 2199, 2217, 2222, 2276, 2276, 2276, 2240, 2276, 2294, 2276, 2276, 2173, 2276, 2198,
  /* 1085 */ 2281, 2281, 2281, 2281, 2282, 2146, 2146, 2146, 2146, 2205, 2146, 2204, 2248, 2276, 2235, 2276, 2297, 2276,
  /* 1103 */ 2276, 2276, 2277, 2256, 2281, 2283, 2146, 2146, 2146, 2275, 2276, 2295, 2276, 2276, 2293, 2146, 2304, 2264,
  /* 1121 */ 2269, 2221, 2276, 2276, 2276, 2293, 2295, 2276, 2276, 2276, 2295, 2263, 2205, 2268, 2220, 2172, 2276, 2276,
  /* 1139 */ 2276, 2296, 2276, 2276, 2296, 2294, 2276, 2276, 2278, 2281, 2281, 2280, 2281, 2281, 2281, 2283, 2206, 2223,
  /* 1157 */ 2276, 2276, 2279, 2281, 2281, 2146, 2273, 2276, 2276, 2281, 2281, 2281, 2276, 2292, 2276, 2298, 2225, 2276,
  /* 1175 */ 2298, 2169, 2224, 2292, 2298, 2171, 2229, 2281, 2281, 2171, 2236, 2281, 2281, 2281, 2146, 2275, 2225, 2292,
  /* 1193 */ 2299, 2276, 2229, 2281, 2146, 2276, 2290, 2297, 2283, 2146, 2146, 2274, 2224, 2227, 2298, 2225, 2297, 2276,
  /* 1211 */ 2230, 2170, 2230, 2282, 2146, 2147, 2151, 2156, 2288, 2276, 2230, 2303, 2308, 2236, 2284, 2228, 2318, 2318,
  /* 1229 */ 2318, 2326, 2335, 2339, 2343, 2349, 2416, 2693, 2357, 2592, 2109, 2592, 2592, 2162, 2943, 2823, 2646, 2592,
  /* 1247 */ 2361, 2592, 2122, 2592, 2592, 2122, 2470, 2592, 2592, 2592, 2109, 2107, 2592, 2592, 2592, 2123, 2592, 2592,
  /* 1265 */ 2592, 2125, 2592, 2413, 2592, 2592, 2592, 2127, 2592, 2592, 2414, 2592, 2592, 2592, 2130, 2952, 2592, 2594,
  /* 1283 */ 2592, 2592, 2212, 2609, 2252, 2592, 2592, 2592, 2446, 2434, 2592, 2592, 2592, 2212, 2446, 2450, 2456, 2431,
  /* 1301 */ 2435, 2592, 2592, 2243, 2478, 2448, 2439, 2946, 2592, 2592, 2592, 2368, 2809, 2813, 2450, 2441, 2212, 2812,
  /* 1319 */ 2449, 2440, 2947, 2592, 2592, 2592, 2345, 2451, 2457, 2948, 2592, 2124, 2592, 2592, 2650, 2823, 2449, 2455,
  /* 1337 */ 2946, 2592, 2128, 2592, 2592, 2649, 2952, 2592, 2810, 2448, 2461, 2991, 2467, 2592, 2592, 2329, 2817, 2474,
  /* 1355 */ 2990, 2466, 2592, 2592, 2373, 2447, 2992, 2469, 2592, 2592, 2592, 2373, 2447, 2477, 2468, 2592, 2592, 2353,
  /* 1373 */ 2469, 2592, 2495, 2592, 2592, 2415, 2483, 2592, 2415, 2496, 2592, 2592, 2352, 2592, 2592, 2352, 2352, 2469,
  /* 1391 */ 2592, 2592, 2363, 2331, 2494, 2592, 2592, 2592, 2375, 2592, 2375, 2415, 2504, 2592, 2592, 2367, 2372, 2503,
  /* 1409 */ 2592, 2592, 2592, 2389, 2418, 2415, 2592, 2592, 2373, 2592, 2592, 2592, 2593, 2732, 2417, 2415, 2592, 2417,
  /* 1427 */ 2520, 2592, 2592, 2592, 2390, 2521, 2521, 2592, 2592, 2592, 2401, 2599, 2585, 2526, 2531, 2120, 2592, 2212,
  /* 1445 */ 2426, 2450, 2463, 2948, 2592, 2592, 2592, 2213, 2389, 2527, 2532, 2121, 2542, 2551, 2105, 2592, 2213, 2592,
  /* 1463 */ 2592, 2592, 2558, 2538, 2544, 2553, 2557, 2537, 2543, 2552, 2421, 2572, 2576, 2546, 2543, 2547, 2592, 2592,
  /* 1481 */ 2373, 2615, 2575, 2545, 2105, 2592, 2244, 2479, 2592, 2129, 2592, 2592, 2628, 2690, 2469, 2562, 2566, 2592,
  /* 1499 */ 2592, 2592, 2415, 2928, 2934, 2401, 2570, 2574, 2564, 2572, 2585, 2590, 2592, 2592, 2585, 2965, 2592, 2592,
  /* 1517 */ 2592, 2445, 2251, 2592, 2592, 2592, 2474, 2592, 2609, 2892, 2592, 2362, 2592, 2592, 2138, 2851, 2159, 2592,
  /* 1535 */ 2592, 2592, 2509, 2888, 2892, 2592, 2592, 2592, 2490, 2418, 2891, 2592, 2592, 2376, 2592, 2592, 2374, 2592,
  /* 1553 */ 2889, 2388, 2592, 2373, 2373, 2890, 2592, 2592, 2387, 2592, 2887, 2505, 2892, 2592, 2373, 2610, 2388, 2592,
  /* 1571 */ 2592, 2376, 2373, 2592, 2887, 2891, 2592, 2374, 2592, 2592, 2608, 2159, 2614, 2620, 2592, 2592, 2394, 2594,
  /* 1589 */ 2887, 2399, 2592, 2887, 2397, 2508, 2374, 2507, 2592, 2375, 2592, 2592, 2592, 2595, 2508, 2506, 2592, 2506,
  /* 1607 */ 2505, 2505, 2592, 2507, 2637, 2505, 2592, 2592, 2401, 2661, 2592, 2643, 2592, 2592, 2417, 2592, 2655, 2592,
  /* 1625 */ 2592, 2592, 2510, 2414, 2656, 2592, 2592, 2592, 2516, 2592, 2593, 2660, 2665, 2880, 2592, 2592, 2592, 2522,
  /* 1643 */ 2767, 2666, 2881, 2592, 2592, 2420, 2571, 2696, 2592, 2592, 2592, 2580, 2572, 2686, 2632, 2698, 2592, 2383,
  /* 1661 */ 2514, 2592, 2163, 2932, 2465, 2685, 2631, 2697, 2592, 2388, 2592, 2592, 2212, 2604, 2671, 2632, 2678, 2592,
  /* 1679 */ 2401, 2405, 2409, 2592, 2592, 2592, 2679, 2592, 2592, 2592, 2592, 2108, 2677, 2591, 2592, 2592, 2592, 2419,
  /* 1697 */ 2592, 2683, 2187, 2191, 2469, 2671, 2189, 2467, 2592, 2401, 2629, 2633, 2702, 2468, 2592, 2592, 2421, 2536,
  /* 1715 */ 2703, 2469, 2592, 2592, 2422, 2573, 2593, 2672, 2467, 2592, 2402, 2406, 2592, 2402, 2979, 2592, 2592, 2626,
  /* 1733 */ 2673, 2467, 2592, 2446, 2259, 2947, 2592, 2377, 2709, 2592, 2592, 2522, 2862, 2713, 2468, 2592, 2592, 2581,
  /* 1751 */ 2572, 2562, 2374, 2374, 2592, 2376, 2721, 2724, 2592, 2592, 2624, 2373, 2731, 2592, 2592, 2592, 2626, 2732,
  /* 1769 */ 2592, 2592, 2592, 2755, 2656, 2726, 2736, 2741, 2592, 2486, 2593, 2381, 2592, 2727, 2737, 2742, 2715, 2747,
  /* 1787 */ 2753, 2592, 2498, 2469, 2873, 2743, 2592, 2592, 2592, 2791, 2759, 2763, 2592, 2592, 2627, 2704, 2592, 2592,
  /* 1805 */ 2522, 2789, 2593, 2761, 2753, 2592, 2498, 2863, 2592, 2592, 2767, 2592, 2592, 2592, 2792, 2789, 2592, 2592,
  /* 1823 */ 2592, 2803, 2126, 2592, 2592, 2592, 2811, 2122, 2592, 2592, 2592, 2834, 2777, 2592, 2592, 2592, 2848, 2936,
  /* 1841 */ 2591, 2489, 2797, 2592, 2592, 2670, 2631, 2490, 2798, 2592, 2592, 2592, 2963, 2807, 2592, 2592, 2592, 2965,
  /* 1859 */ 2838, 2592, 2592, 2592, 2975, 2330, 2818, 2829, 2592, 2498, 2939, 2592, 2498, 2592, 2791, 2331, 2819, 2830,
  /* 1877 */ 2592, 2592, 2592, 2982, 2834, 2817, 2828, 2106, 2592, 2592, 2592, 2405, 2405, 2817, 2828, 2592, 2592, 2415,
  /* 1895 */ 2849, 2842, 2592, 2522, 2773, 2592, 2522, 2868, 2592, 2580, 2600, 2586, 2137, 2850, 2843, 2592, 2592, 2855,
  /* 1913 */ 2937, 2844, 2592, 2592, 2592, 2987, 2936, 2591, 2592, 2592, 2684, 2630, 2592, 2856, 2938, 2592, 2592, 2860,
  /* 1931 */ 2939, 2592, 2592, 2872, 2592, 2861, 2591, 2592, 2592, 2887, 2616, 2592, 2867, 2592, 2592, 2708, 2592, 2498,
  /* 1949 */ 2469, 2498, 2497, 2785, 2773, 2499, 2783, 2770, 2877, 2877, 2877, 2772, 2592, 2592, 2345, 2885, 2592, 2592,
  /* 1967 */ 2592, 2715, 2762, 2515, 2896, 2592, 2592, 2715, 2917, 2516, 2897, 2592, 2592, 2592, 2901, 2906, 2911, 2592,
  /* 1985 */ 2592, 2956, 2960, 2715, 2902, 2907, 2912, 2593, 2916, 2920, 2820, 2922, 2822, 2592, 2592, 2715, 2927, 2921,
  /* 2003 */ 2821, 2106, 2592, 2592, 2974, 2408, 2321, 2821, 2106, 2592, 2592, 2983, 2592, 2593, 2404, 2408, 2592, 2592,
  /* 2021 */ 2717, 2749, 2716, 2928, 2322, 2822, 2593, 2926, 2919, 2820, 2934, 2823, 2592, 2592, 2592, 2651, 2824, 2592,
  /* 2039 */ 2592, 2592, 2130, 2952, 2592, 2592, 2592, 2592, 2964, 2592, 2592, 2716, 2748, 2592, 2969, 2592, 2592, 2716,
  /* 2057 */ 2918, 2368, 2970, 2592, 2592, 2592, 2403, 2407, 2592, 2592, 2787, 2211, 2404, 2409, 2592, 2592, 2802, 2837,
  /* 2075 */ 2987, 2592, 2592, 2592, 2809, 2427, 2592, 2793, 2592, 2592, 2809, 2447, 1073741824, 0x80000000, 539754496,
  /* 2090 */ 542375936, 402653184, 554434560, 571736064, 545521856, 268451840, 335544320, 268693630, 512, 2048, 256,
  /* 2101 */ 1024, 0, 1024, 0, 1073741824, 0x80000000, 0, 0, 0, 8388608, 0, 0, 1073741824, 1073741824, 0, 0x80000000,
  /* 2117 */ 537133056, 4194304, 1048576, 268435456, -1073741824, 0, 0, 0, 1048576, 0, 0, 0, 1572864, 0, 0, 0, 4194304,
  /* 2134 */ 0, 134217728, 16777216, 0, 0, 32, 64, 98304, 0, 33554432, 8388608, 192, 67108864, 67108864, 67108864,
  /* 2149 */ 67108864, 16, 32, 4, 0, 8192, 196608, 196608, 229376, 80, 4096, 524288, 8388608, 0, 0, 32, 128, 256, 24576,
  /* 2168 */ 24600, 24576, 24576, 2, 24576, 24576, 24576, 24584, 24592, 24576, 24578, 24576, 24578, 24576, 24576, 16,
  /* 2184 */ 512, 2048, 2048, 256, 4096, 32768, 1048576, 4194304, 67108864, 134217728, 268435456, 262144, 134217728, 0,
  /* 2198 */ 128, 128, 64, 16384, 16384, 16384, 67108864, 32, 32, 4, 4, 4096, 262144, 134217728, 0, 0, 0, 2, 0, 8192,
  /* 2218 */ 131072, 131072, 4096, 4096, 4096, 4096, 24576, 24576, 24576, 8, 8, 24576, 24576, 16384, 16384, 16384,
  /* 2234 */ 24576, 24584, 24576, 24576, 24576, 16384, 24576, 536870912, 262144, 0, 0, 32, 2048, 8192, 4, 4096, 4096,
  /* 2251 */ 4096, 786432, 8388608, 16777216, 0, 128, 16384, 16384, 16384, 32768, 65536, 2097152, 32, 32, 32, 32, 4, 4,
  /* 2269 */ 4, 4, 4, 4096, 67108864, 67108864, 67108864, 24576, 24576, 24576, 24576, 0, 16384, 16384, 16384, 16384,
  /* 2285 */ 67108864, 67108864, 8, 67108864, 24576, 8, 8, 8, 24576, 24576, 24576, 24578, 24576, 24576, 24576, 2, 2, 2,
  /* 2303 */ 16384, 67108864, 67108864, 67108864, 32, 67108864, 8, 8, 24576, 2048, 0x80000000, 536870912, 262144,
  /* 2316 */ 262144, 262144, 67108864, 8, 24576, 16384, 32768, 1048576, 4194304, 25165824, 67108864, 24576, 32770, 2, 4,
  /* 2331 */ 112, 512, 98304, 524288, 50, 402653186, 1049090, 1049091, 10, 66, 100925514, 10, 66, 12582914, 0, 0,
  /* 2347 */ -1678194207, -1678194207, -1041543218, 0, 32768, 0, 0, 32, 65536, 268435456, 1, 1, 513, 1048577, 0,
  /* 2362 */ 12582912, 0, 0, 0, 4, 1792, 0, 0, 0, 7, 29360128, 0, 0, 0, 8, 0, 0, 0, 12, 1, 1, 0, 0, -604102721,
  /* 2386 */ -604102721, 4194304, 8388608, 0, 0, 0, 31, 925600, 997981306, 997981306, 997981306, 0, 0, 2048, 8388608, 0,
  /* 2402 */ 0, 1, 2, 4, 32, 64, 512, 8192, 0, 0, 0, 245760, 997720064, 0, 0, 0, 32, 0, 0, 0, 3, 12, 16, 32, 8, 112,
  /* 2428 */ 3072, 12288, 16384, 32768, 65536, 131072, 7864320, 16777216, 973078528, 0, 0, 65536, 131072, 3670016,
  /* 2442 */ 4194304, 16777216, 33554432, 2, 8, 48, 2048, 8192, 16384, 32768, 65536, 131072, 524288, 131072, 524288,
  /* 2457 */ 3145728, 4194304, 16777216, 33554432, 65536, 131072, 2097152, 4194304, 16777216, 33554432, 134217728,
  /* 2468 */ 268435456, 536870912, 0, 0, 0, 1024, 0, 8, 48, 2048, 8192, 65536, 33554432, 268435456, 536870912, 65536,
  /* 2484 */ 268435456, 536870912, 0, 0, 32768, 0, 0, 126, 623104, 65011712, 0, 32, 65536, 536870912, 0, 0, 65536,
  /* 2501 */ 524288, 0, 32, 65536, 0, 0, 0, 2048, 0, 0, 0, 15482, 245760, -604102721, 0, 0, 0, 18913, 33062912, 925600,
  /* 2521 */ -605028352, 0, 0, 0, 65536, 31, 8096, 131072, 786432, 3145728, 3145728, 12582912, 50331648, 134217728,
  /* 2535 */ 268435456, 160, 256, 512, 7168, 131072, 786432, 131072, 786432, 1048576, 2097152, 12582912, 16777216,
  /* 2548 */ 268435456, 1073741824, 0x80000000, 12582912, 16777216, 33554432, 268435456, 1073741824, 0x80000000, 3, 12,
  /* 2559 */ 16, 160, 256, 7168, 786432, 1048576, 12582912, 16777216, 268435456, 1073741824, 0, 8, 16, 32, 128, 256,
  /* 2575 */ 512, 7168, 786432, 1048576, 2097152, 0, 1, 2, 8, 16, 7168, 786432, 1048576, 8388608, 16777216, 16777216,
  /* 2591 */ 1073741824, 0, 0, 0, 0, 1, 0, 0, 8, 32, 128, 256, 7168, 8, 32, 0, 3072, 0, 8, 32, 3072, 4096, 524288, 8,
  /* 2615 */ 32, 0, 0, 3072, 4096, 0, 2048, 524288, 8388608, 8, 2048, 0, 0, 1, 12, 256, 4096, 32768, 262144, 1048576,
  /* 2635 */ 4194304, 67108864, 0, 2048, 0, 2048, 2048, 1073741824, -58805985, -58805985, -58805985, 0, 0, 262144, 0, 0,
  /* 2651 */ 32, 4194304, 16777216, 134217728, 4382, 172032, -58982400, 0, 0, 2, 28, 256, 4096, 8192, 8192, 32768,
  /* 2667 */ 131072, 262144, 524288, 1, 2, 12, 256, 4096, 0, 0, 4194304, 67108864, 134217728, 805306368, 1073741824, 0,
  /* 2683 */ 0, 1, 2, 12, 16, 256, 4096, 1048576, 67108864, 134217728, 268435456, 0, 512, 1048576, 4194304, 201326592,
  /* 2699 */ 1879048192, 0, 0, 12, 256, 4096, 134217728, 268435456, 536870912, 12, 256, 268435456, 536870912, 0, 12,
  /* 2714 */ 256, 0, 0, 1, 32, 64, 512, 0, 0, 205236961, 205236961, 0, 0, 0, 1, 96, 640, 1, 10976, 229376, 204996608, 0,
  /* 2736 */ 640, 2048, 8192, 229376, 1572864, 1572864, 2097152, 201326592, 0, 0, 0, 64, 512, 2048, 229376, 1572864,
  /* 2752 */ 201326592, 1572864, 201326592, 0, 0, 1, 4382, 0, 1, 32, 2048, 65536, 131072, 1572864, 201326592, 131072,
  /* 2768 */ 1572864, 134217728, 0, 0, 524288, 524288, 0, 0, 0, -68582786, -68582786, -68582786, 0, 0, 2097152, 524288,
  /* 2784 */ 0, 524288, 0, 0, 65536, 131072, 1572864, 0, 0, 2, 4, 0, 0, 65011712, -134217728, 0, 0, 0, 0, 2, 4, 120,
  /* 2806 */ 512, -268435456, 0, 0, 0, 2, 8, 48, 64, 2048, 8192, 98304, 524288, 2097152, 4194304, 25165824, 33554432,
  /* 2823 */ 134217728, 268435456, 0x80000000, 0, 0, 25165824, 33554432, 134217728, 1879048192, 0x80000000, 0, 0, 4,
  /* 2836 */ 112, 512, 622592, 65011712, 134217728, -268435456, 16777216, 33554432, 134217728, 1610612736, 0, 0, 0, 64,
  /* 2850 */ 98304, 524288, 4194304, 16777216, 33554432, 0, 98304, 524288, 16777216, 33554432, 0, 65536, 524288,
  /* 2863 */ 33554432, 536870912, 1073741824, 0, 65536, 524288, 536870912, 1073741824, 0, 0, 65536, 524288, 536870912,
  /* 2876 */ 0, 524288, 0, 524288, 524288, 1048576, 2086666240, 0x80000000, 0, -1678194207, 0, 0, 0, 8, 32, 2048,
  /* 2892 */ 524288, 8388608, 0, 0, 33062912, 436207616, 0x80000000, 0, 0, 32, 64, 2432, 16384, 32768, 32768, 524288,
  /* 2908 */ 3145728, 4194304, 25165824, 25165824, 167772160, 268435456, 0x80000000, 0, 32, 64, 384, 2048, 16384, 32768,
  /* 2922 */ 1048576, 2097152, 4194304, 25165824, 32, 64, 128, 256, 2048, 16384, 2048, 16384, 1048576, 4194304,
  /* 2936 */ 16777216, 33554432, 134217728, 536870912, 1073741824, 0, 0, 2048, 16384, 4194304, 16777216, 33554432,
  /* 2948 */ 134217728, 805306368, 0, 0, 16777216, 134217728, 268435456, 0x80000000, 0, 622592, 622592, 622592, 8807,
  /* 2961 */ 8807, 434791, 0, 0, 16777216, 0, 0, 0, 7, 608, 8192, 0, 0, 0, 3, 4, 96, 512, 32, 64, 8192, 0, 0, 16777216,
  /* 2985 */ 134217728, 0, 0, 2, 4, 8192, 16384, 65536, 2097152, 33554432, 268435456
];

XQueryTokenizer.TOKEN =
[
  "(0)",
  "ModuleDecl",
  "Annotation",
  "OptionDecl",
  "Operator",
  "Variable",
  "Tag",
  "EndTag",
  "PragmaContents",
  "DirCommentContents",
  "DirPIContents",
  "CDataSectionContents",
  "AttrTest",
  "Wildcard",
  "EQName",
  "IntegerLiteral",
  "DecimalLiteral",
  "DoubleLiteral",
  "PredefinedEntityRef",
  "'\"\"'",
  "EscapeApos",
  "QuotChar",
  "AposChar",
  "ElementContentChar",
  "QuotAttrContentChar",
  "AposAttrContentChar",
  "NCName",
  "QName",
  "S",
  "CharRef",
  "CommentContents",
  "DocTag",
  "DocCommentContents",
  "EOF",
  "'!'",
  "'\"'",
  "'#'",
  "'#)'",
  "''''",
  "'('",
  "'(#'",
  "'(:'",
  "'(:~'",
  "')'",
  "'*'",
  "'*'",
  "','",
  "'-->'",
  "'.'",
  "'/'",
  "'/>'",
  "':'",
  "':)'",
  "';'",
  "'<!--'",
  "'<![CDATA['",
  "'<?'",
  "'='",
  "'>'",
  "'?'",
  "'?>'",
  "'NaN'",
  "'['",
  "']'",
  "']]>'",
  "'after'",
  "'all'",
  "'allowing'",
  "'ancestor'",
  "'ancestor-or-self'",
  "'and'",
  "'any'",
  "'append'",
  "'array'",
  "'as'",
  "'ascending'",
  "'at'",
  "'attribute'",
  "'base-uri'",
  "'before'",
  "'boundary-space'",
  "'break'",
  "'by'",
  "'case'",
  "'cast'",
  "'castable'",
  "'catch'",
  "'check'",
  "'child'",
  "'collation'",
  "'collection'",
  "'comment'",
  "'constraint'",
  "'construction'",
  "'contains'",
  "'content'",
  "'context'",
  "'continue'",
  "'copy'",
  "'copy-namespaces'",
  "'count'",
  "'decimal-format'",
  "'decimal-separator'",
  "'declare'",
  "'default'",
  "'delete'",
  "'descendant'",
  "'descendant-or-self'",
  "'descending'",
  "'diacritics'",
  "'different'",
  "'digit'",
  "'distance'",
  "'div'",
  "'document'",
  "'document-node'",
  "'element'",
  "'else'",
  "'empty'",
  "'empty-sequence'",
  "'encoding'",
  "'end'",
  "'entire'",
  "'eq'",
  "'every'",
  "'exactly'",
  "'except'",
  "'exit'",
  "'external'",
  "'first'",
  "'following'",
  "'following-sibling'",
  "'for'",
  "'foreach'",
  "'foreign'",
  "'from'",
  "'ft-option'",
  "'ftand'",
  "'ftnot'",
  "'ftor'",
  "'function'",
  "'ge'",
  "'greatest'",
  "'group'",
  "'grouping-separator'",
  "'gt'",
  "'idiv'",
  "'if'",
  "'import'",
  "'in'",
  "'index'",
  "'infinity'",
  "'inherit'",
  "'insensitive'",
  "'insert'",
  "'instance'",
  "'integrity'",
  "'intersect'",
  "'into'",
  "'is'",
  "'item'",
  "'json'",
  "'json-item'",
  "'key'",
  "'language'",
  "'last'",
  "'lax'",
  "'le'",
  "'least'",
  "'let'",
  "'levels'",
  "'loop'",
  "'lowercase'",
  "'lt'",
  "'minus-sign'",
  "'mod'",
  "'modify'",
  "'module'",
  "'most'",
  "'namespace'",
  "'namespace-node'",
  "'ne'",
  "'next'",
  "'no'",
  "'no-inherit'",
  "'no-preserve'",
  "'node'",
  "'nodes'",
  "'not'",
  "'object'",
  "'occurs'",
  "'of'",
  "'on'",
  "'only'",
  "'option'",
  "'or'",
  "'order'",
  "'ordered'",
  "'ordering'",
  "'paragraph'",
  "'paragraphs'",
  "'parent'",
  "'pattern-separator'",
  "'per-mille'",
  "'percent'",
  "'phrase'",
  "'position'",
  "'preceding'",
  "'preceding-sibling'",
  "'preserve'",
  "'previous'",
  "'processing-instruction'",
  "'relationship'",
  "'rename'",
  "'replace'",
  "'return'",
  "'returning'",
  "'revalidation'",
  "'same'",
  "'satisfies'",
  "'schema'",
  "'schema-attribute'",
  "'schema-element'",
  "'score'",
  "'self'",
  "'sensitive'",
  "'sentence'",
  "'sentences'",
  "'skip'",
  "'sliding'",
  "'some'",
  "'stable'",
  "'start'",
  "'stemming'",
  "'stop'",
  "'strict'",
  "'strip'",
  "'structured-item'",
  "'switch'",
  "'text'",
  "'then'",
  "'thesaurus'",
  "'times'",
  "'to'",
  "'treat'",
  "'try'",
  "'tumbling'",
  "'type'",
  "'typeswitch'",
  "'union'",
  "'unique'",
  "'unordered'",
  "'updating'",
  "'uppercase'",
  "'using'",
  "'validate'",
  "'value'",
  "'variable'",
  "'version'",
  "'weight'",
  "'when'",
  "'where'",
  "'while'",
  "'wildcards'",
  "'window'",
  "'with'",
  "'without'",
  "'word'",
  "'words'",
  "'xquery'",
  "'zero-digit'",
  "'{'",
  "'{{'",
  "'|'",
  "'}'",
  "'}}'"
];

// End

},
{}],
2:[function(_dereq_,module,exports){
'use strict';

var TokenHandler = function(code) {
    var input = code;
    this.tokens = [];
 
    this.reset = function() {
        input = input;
        this.tokens = [];
    };
    
    this.startNonterminal = function() {};
    this.endNonterminal = function() {};

    this.terminal = function(name, begin, end) {
        this.tokens.push({
            name: name,
            value: input.substring(begin, end)
        });
    };

    this.whitespace = function(begin, end) {
        this.tokens.push({
            name: 'WS',
            value: input.substring(begin, end)
        });
    };
};

exports.Lexer = function(Tokenizer, Rules) {

    this.tokens = [];
  
    this.getLineTokens = function(line, state) {
        state = (state === 'start' || !state) ? '["start"]' : state;
        var stack = JSON.parse(state);
        var h = new TokenHandler(line);
        var tokenizer = new Tokenizer(line, h);
        var tokens = [];
    
        while(true) {
            var currentState = stack[stack.length - 1];
            try {
                h.tokens = [];
                tokenizer['parse_' + currentState]();
                var info = null;
        
                if(h.tokens.length > 1 && h.tokens[0].name === 'WS') {
                    tokens.push({
                        type: 'text',
                        value: h.tokens[0].value
                    });
                    h.tokens.splice(0, 1);
                }
        
                var token = h.tokens[0];
                var rules  = Rules[currentState];
                for(var k = 0; k < rules.length; k++) {
                    var rule = Rules[currentState][k];
                    if((typeof(rule.name) === 'function' && rule.name(token)) || rule.name === token.name) {
                        info = rule;
                        break;
                    }
                }
        
                if(token.name === 'EOF') { break; }
                if(token.value === '') { throw 'Encountered empty string lexical rule.'; }
        
                tokens.push({
                    type: info === null ? 'text' : (typeof(info.token) === 'function' ? info.token(token.value) : info.token),
                    value: token.value
                });
        
                if(info && info.next) {
                    info.next(stack);
                }
      
            } catch(e) {
                if(e instanceof tokenizer.ParseException) {
                    var index = 0;
                    for(var i=0; i < tokens.length; i++) {
                        index += tokens[i].value.length;
                    }
                    tokens.push({ type: 'text', value: line.substring(index) });
                    return {
                        tokens: tokens,
                        state: JSON.stringify(['start'])
                    };
                } else {
                    throw e;
                }
            }
        }

        return {
            tokens: tokens,
            state: JSON.stringify(stack)
        };
    };
};
},
{}],
3:[function(_dereq_,module,exports){
'use strict';

var XQueryTokenizer = _dereq_('./XQueryTokenizer').XQueryTokenizer;
var Lexer = _dereq_('./lexer').Lexer;

var keys = 'after|ancestor|ancestor-or-self|and|as|ascending|attribute|before|case|cast|castable|child|collation|comment|copy|count|declare|default|delete|descendant|descendant-or-self|descending|div|document|document-node|element|else|empty|empty-sequence|end|eq|every|except|first|following|following-sibling|for|function|ge|group|gt|idiv|if|import|insert|instance|intersect|into|is|item|last|le|let|lt|mod|modify|module|namespace|namespace-node|ne|node|only|or|order|ordered|parent|preceding|preceding-sibling|processing-instruction|rename|replace|return|satisfies|schema-attribute|schema-element|self|some|stable|start|switch|text|to|treat|try|typeswitch|union|unordered|validate|where|with|xquery|contains|paragraphs|sentences|times|words|by|collectionreturn|variable|version|option|when|encoding|toswitch|catch|tumbling|sliding|window|at|using|stemming|collection|schema|while|on|nodes|index|external|then|in|updating|value|of|containsbreak|loop|continue|exit|returning|append|json|position|strict'.split('|');

var keywords = keys.map(function(val) { return { name: '\'' + val + '\'', token: 'keyword' }; });
var ncnames = keys.map(function(val) { return { name: '\'' + val + '\'', token: 'text', next: function(stack){ stack.pop(); } }; });

var cdata = 'constant.language';
var number = 'constant';
var xmlcomment = 'comment';
var pi = 'xml-pe';
var pragma = 'constant.buildin';
var n = function(name){
    return '\'' + name + '\'';
};
var Rules = {
    start: [
        { name: n('(#'), token: pragma, next: function(stack){ stack.push('Pragma'); } },
        { name: n('(:'), token: 'comment', next: function(stack){ stack.push('Comment'); } },
        { name: n('(:~'), token: 'comment.doc', next: function(stack){ stack.push('CommentDoc'); } },
        { name: n('<!--'), token: xmlcomment, next: function(stack){ stack.push('XMLComment'); } },
        { name: n('<?'), token: pi, next: function(stack) { stack.push('PI'); } },
        { name: n('\'\''), token: 'string', next: function(stack){ stack.push('AposString'); } },
        { name: n('"'), token: 'string', next: function(stack){ stack.push('QuotString'); } },
        { name: 'Annotation', token: 'support.function' },
        { name: 'ModuleDecl', token: 'keyword', next: function(stack){ stack.push('Prefix'); } },
        { name: 'OptionDecl', token: 'keyword', next: function(stack){ stack.push('_EQName'); } },
        { name: 'AttrTest', token: 'support.type' },
        { name: 'Variable', token: 'variable' },
        { name: n('<![CDATA['), token: cdata, next: function(stack){ stack.push('CData'); } },
        { name: 'IntegerLiteral', token: number },
        { name: 'DecimalLiteral', token: number },
        { name: 'DoubleLiteral', token: number },
        { name: 'Operator', token: 'keyword.operator' },
        { name: 'EQName', token: function(val) { return keys.indexOf(val) !== -1 ? 'keyword' : 'support.function'; } },
        { name: n('('), token: 'lparen' },
        { name: n(')'), token: 'rparen' },
        { name: 'Tag', token: 'meta.tag', next: function(stack){ stack.push('StartTag'); } },
        { name: n('}'), token: 'text', next: function(stack){ if(stack.length > 1) { stack.pop(); } } },
        { name: n('{'), token: 'text', next: function(stack){ stack.push('start'); } } //, next: function(stack){ if(stack.length > 1) { stack.pop(); } } }
    ].concat(keywords),
    _EQName: [
        { name: 'EQName', token: 'text', next: function(stack) { stack.pop(); } }
    ].concat(ncnames),
    Prefix: [
        { name: 'NCName', token: 'text', next: function(stack) { stack.pop(); } }
    ].concat(ncnames),
    StartTag: [
        { name: n('>'), token: 'meta.tag', next: function(stack){ stack.push('TagContent'); } },
        { name: 'QName', token: 'entity.other.attribute-name' },
        { name: n('='), token: 'text' },
        { name: n('\'\''), token: 'string', next: function(stack){ stack.push('AposAttr'); } },
        { name: n('"'), token: 'string', next: function(stack){ stack.push('QuotAttr'); } },
        { name: n('/>'), token: 'meta.tag.r', next: function(stack){ stack.pop(); } }
    ],
    TagContent: [
        { name: 'ElementContentChar', token: 'text' },
        { name: n('<![CDATA['), token: cdata, next: function(stack){ stack.push('CData'); } },
        { name: n('<!--'), token: xmlcomment, next: function(stack){ stack.push('XMLComment'); } },
        { name: 'Tag', token: 'meta.tag', next: function(stack){ stack.push('StartTag'); } },
        { name: 'PredefinedEntityRef', token: 'constant.language.escape' },
        { name: 'CharRef', token: 'constant.language.escape' },
        { name: n('{{'), token: 'text' },
        { name: n('}}'), token: 'text' },
        { name: n('{'), token: 'text', next: function(stack){ stack.push('start'); } },
        { name: 'EndTag', token: 'meta.tag', next: function(stack){ stack.pop(); stack.pop(); } }
    ],
    AposAttr: [
        { name: n('\'\''), token: 'string', next: function(stack){ stack.pop(); } },
        { name: 'EscapeApos', token: 'constant.language.escape' },
        { name: 'AposAttrContentChar', token: 'string' },
        { name: 'PredefinedEntityRef', token: 'constant.language.escape' },
        { name: 'CharRef', token: 'constant.language.escape' },
        { name: n('{{'), token: 'string' },
        { name: n('}}'), token: 'string' },
        { name: n('{'), token: 'text', next: function(stack){ stack.push('start'); } }
    ],
    QuotAttr: [
        { name: n('\"'), token: 'string', next: function(stack){ stack.pop(); } },
        { name: 'EscapeQuot', token: 'constant.language.escape' },
        { name: 'QuotAttrContentChar', token: 'string' },
        { name: 'PredefinedEntityRef', token: 'constant.language.escape' },
        { name: 'CharRef', token: 'constant.language.escape' },
        { name: n('{{'), token: 'string' },
        { name: n('}}'), token: 'string' },
        { name: n('{'), token: 'text', next: function(stack){ stack.push('start'); } }
    ],
    Pragma: [
        { name: 'PragmaContents', token: pragma },
        { name: n('#'), token: pragma },
        { name: n('#)'), token: pragma, next: function(stack){ stack.pop(); } }
    ],
    Comment: [
        { name: 'CommentContents', token: 'comment' },
        { name: n('(:'), token: 'comment', next: function(stack){ stack.push('Comment'); } },
        { name: n(':)'), token: 'comment', next: function(stack){ stack.pop(); } }
    ],
    CommentDoc: [
        { name: 'DocCommentContents', token: 'comment.doc' },
        { name: 'DocTag', token: 'comment.doc.tag' },
        { name: n('(:'), token: 'comment.doc', next: function(stack){ stack.push('CommentDoc'); } },
        { name: n(':)'), token: 'comment.doc', next: function(stack){ stack.pop(); } }
    ],
    XMLComment: [
        { name: 'DirCommentContents', token: xmlcomment },
        { name: n('-->'), token: xmlcomment, next: function(stack){ stack.pop(); } }
    ],
    CData: [
        { name: 'CDataSectionContents', token: cdata },
        { name: n(']]>'), token: cdata, next: function(stack){ stack.pop(); } }
    ],
    PI: [
        { name: 'DirPIContents', token: pi },
        { name: n('?'), token: pi },
        { name: n('?>'), token: pi, next: function(stack){ stack.pop(); } }
    ],
    AposString: [
        { name: n('\'\''), token: 'string', next: function(stack){ stack.pop(); } },
        { name: 'PredefinedEntityRef', token: 'constant.language.escape' },
        { name: 'CharRef', token: 'constant.language.escape' },
        { name: 'EscapeApos', token: 'constant.language.escape' },
        { name: 'AposChar', token: 'string' }
    ],
    QuotString: [
        { name: n('"'), token: 'string', next: function(stack){ stack.pop(); } },
        { name: 'PredefinedEntityRef', token: 'constant.language.escape' },
        { name: 'CharRef', token: 'constant.language.escape' },
        { name: 'EscapeQuot', token: 'constant.language.escape' },
        { name: 'QuotChar', token: 'string' }
    ]
};
    
exports.XQueryLexer = function(){ return new Lexer(XQueryTokenizer, Rules); };
},
{"./XQueryTokenizer":1,"./lexer":2}]},{},[3])
(3)

});