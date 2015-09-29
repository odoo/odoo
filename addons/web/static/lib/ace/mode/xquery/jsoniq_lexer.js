define(function(require, exports, module) {
module.exports = (function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);throw new Error("Cannot find module '"+o+"'")}var f=n[o]={exports:{}};t[o][0].call(f.exports,function(e){var n=t[o][1][e];return s(n?n:e)},f,f.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({
1:[function(_dereq_,module,exports){
// This file was generated on Thu Jul 24, 2014 15:01 (UTC+01) by REx v5.30 which is Copyright (c) 1979-2014 by Gunther Rademacher <grd@gmx.net>
// REx command line: JSONiqTokenizer.ebnf -ll 2 -backtrack -tree -javascript -a xqlint

                                                            // line 2 "JSONiqTokenizer.ebnf"
                                                            var JSONiqTokenizer = exports.JSONiqTokenizer = function JSONiqTokenizer(string, parsingEventHandler)
                                                            {
                                                              init(string, parsingEventHandler);
                                                            // line 9 "JSONiqTokenizer.js"
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
    return o >= 0 ? JSONiqTokenizer.TOKEN[o] : null;
  };

  this.getExpectedTokenSet = function(e)
  {
    var expected;
    if (e.getExpected() < 0)
    {
      expected = JSONiqTokenizer.getTokenSet(- e.getState());
    }
    else
    {
      expected = [JSONiqTokenizer.TOKEN[e.getExpected()]];
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
                                    // S^WS | EOF | '!' | '"' | '$$' | "'" | '(' | '(#' | '(:' | '(:~' | ')' | ',' |
                                    // '.' | '/' | ':' | ';' | '<!--' | '<![CDATA[' | '<?' | '[' | ']' | 'after' |
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
    case 58:                        // '<![CDATA['
      shift(58);                    // '<![CDATA['
      break;
    case 57:                        // '<!--'
      shift(57);                    // '<!--'
      break;
    case 59:                        // '<?'
      shift(59);                    // '<?'
      break;
    case 43:                        // '(#'
      shift(43);                    // '(#'
      break;
    case 45:                        // '(:~'
      shift(45);                    // '(:~'
      break;
    case 44:                        // '(:'
      shift(44);                    // '(:'
      break;
    case 37:                        // '"'
      shift(37);                    // '"'
      break;
    case 41:                        // "'"
      shift(41);                    // "'"
      break;
    case 277:                       // '}'
      shift(277);                   // '}'
      break;
    case 274:                       // '{'
      shift(274);                   // '{'
      break;
    case 42:                        // '('
      shift(42);                    // '('
      break;
    case 46:                        // ')'
      shift(46);                    // ')'
      break;
    case 52:                        // '/'
      shift(52);                    // '/'
      break;
    case 65:                        // '['
      shift(65);                    // '['
      break;
    case 66:                        // ']'
      shift(66);                    // ']'
      break;
    case 49:                        // ','
      shift(49);                    // ','
      break;
    case 51:                        // '.'
      shift(51);                    // '.'
      break;
    case 56:                        // ';'
      shift(56);                    // ';'
      break;
    case 54:                        // ':'
      shift(54);                    // ':'
      break;
    case 36:                        // '!'
      shift(36);                    // '!'
      break;
    case 276:                       // '|'
      shift(276);                   // '|'
      break;
    case 40:                        // '$$'
      shift(40);                    // '$$'
      break;
    case 5:                         // Annotation
      shift(5);                     // Annotation
      break;
    case 4:                         // ModuleDecl
      shift(4);                     // ModuleDecl
      break;
    case 6:                         // OptionDecl
      shift(6);                     // OptionDecl
      break;
    case 15:                        // AttrTest
      shift(15);                    // AttrTest
      break;
    case 16:                        // Wildcard
      shift(16);                    // Wildcard
      break;
    case 18:                        // IntegerLiteral
      shift(18);                    // IntegerLiteral
      break;
    case 19:                        // DecimalLiteral
      shift(19);                    // DecimalLiteral
      break;
    case 20:                        // DoubleLiteral
      shift(20);                    // DoubleLiteral
      break;
    case 8:                         // Variable
      shift(8);                     // Variable
      break;
    case 9:                         // Tag
      shift(9);                     // Tag
      break;
    case 7:                         // Operator
      shift(7);                     // Operator
      break;
    case 35:                        // EOF
      shift(35);                    // EOF
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
    case 61:                        // '>'
      shift(61);                    // '>'
      break;
    case 53:                        // '/>'
      shift(53);                    // '/>'
      break;
    case 29:                        // QName
      shift(29);                    // QName
      break;
    case 60:                        // '='
      shift(60);                    // '='
      break;
    case 37:                        // '"'
      shift(37);                    // '"'
      break;
    case 41:                        // "'"
      shift(41);                    // "'"
      break;
    default:
      shift(35);                    // EOF
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
    case 25:                        // ElementContentChar
      shift(25);                    // ElementContentChar
      break;
    case 9:                         // Tag
      shift(9);                     // Tag
      break;
    case 10:                        // EndTag
      shift(10);                    // EndTag
      break;
    case 58:                        // '<![CDATA['
      shift(58);                    // '<![CDATA['
      break;
    case 57:                        // '<!--'
      shift(57);                    // '<!--'
      break;
    case 21:                        // PredefinedEntityRef
      shift(21);                    // PredefinedEntityRef
      break;
    case 31:                        // CharRef
      shift(31);                    // CharRef
      break;
    case 275:                       // '{{'
      shift(275);                   // '{{'
      break;
    case 278:                       // '}}'
      shift(278);                   // '}}'
      break;
    case 274:                       // '{'
      shift(274);                   // '{'
      break;
    default:
      shift(35);                    // EOF
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
    case 23:                        // EscapeApos
      shift(23);                    // EscapeApos
      break;
    case 27:                        // AposAttrContentChar
      shift(27);                    // AposAttrContentChar
      break;
    case 21:                        // PredefinedEntityRef
      shift(21);                    // PredefinedEntityRef
      break;
    case 31:                        // CharRef
      shift(31);                    // CharRef
      break;
    case 275:                       // '{{'
      shift(275);                   // '{{'
      break;
    case 278:                       // '}}'
      shift(278);                   // '}}'
      break;
    case 274:                       // '{'
      shift(274);                   // '{'
      break;
    case 41:                        // "'"
      shift(41);                    // "'"
      break;
    default:
      shift(35);                    // EOF
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
    case 22:                        // EscapeQuot
      shift(22);                    // EscapeQuot
      break;
    case 26:                        // QuotAttrContentChar
      shift(26);                    // QuotAttrContentChar
      break;
    case 21:                        // PredefinedEntityRef
      shift(21);                    // PredefinedEntityRef
      break;
    case 31:                        // CharRef
      shift(31);                    // CharRef
      break;
    case 275:                       // '{{'
      shift(275);                   // '{{'
      break;
    case 278:                       // '}}'
      shift(278);                   // '}}'
      break;
    case 274:                       // '{'
      shift(274);                   // '{'
      break;
    case 37:                        // '"'
      shift(37);                    // '"'
      break;
    default:
      shift(35);                    // EOF
    }
    eventHandler.endNonterminal("QuotAttr", e0);
  };

  this.parse_CData = function()
  {
    eventHandler.startNonterminal("CData", e0);
    lookahead1(1);                  // CDataSectionContents | EOF | ']]>'
    switch (l1)
    {
    case 14:                        // CDataSectionContents
      shift(14);                    // CDataSectionContents
      break;
    case 67:                        // ']]>'
      shift(67);                    // ']]>'
      break;
    default:
      shift(35);                    // EOF
    }
    eventHandler.endNonterminal("CData", e0);
  };

  this.parse_XMLComment = function()
  {
    eventHandler.startNonterminal("XMLComment", e0);
    lookahead1(0);                  // DirCommentContents | EOF | '-->'
    switch (l1)
    {
    case 12:                        // DirCommentContents
      shift(12);                    // DirCommentContents
      break;
    case 50:                        // '-->'
      shift(50);                    // '-->'
      break;
    default:
      shift(35);                    // EOF
    }
    eventHandler.endNonterminal("XMLComment", e0);
  };

  this.parse_PI = function()
  {
    eventHandler.startNonterminal("PI", e0);
    lookahead1(3);                  // DirPIContents | EOF | '?' | '?>'
    switch (l1)
    {
    case 13:                        // DirPIContents
      shift(13);                    // DirPIContents
      break;
    case 62:                        // '?'
      shift(62);                    // '?'
      break;
    case 63:                        // '?>'
      shift(63);                    // '?>'
      break;
    default:
      shift(35);                    // EOF
    }
    eventHandler.endNonterminal("PI", e0);
  };

  this.parse_Pragma = function()
  {
    eventHandler.startNonterminal("Pragma", e0);
    lookahead1(2);                  // PragmaContents | EOF | '#' | '#)'
    switch (l1)
    {
    case 11:                        // PragmaContents
      shift(11);                    // PragmaContents
      break;
    case 38:                        // '#'
      shift(38);                    // '#'
      break;
    case 39:                        // '#)'
      shift(39);                    // '#)'
      break;
    default:
      shift(35);                    // EOF
    }
    eventHandler.endNonterminal("Pragma", e0);
  };

  this.parse_Comment = function()
  {
    eventHandler.startNonterminal("Comment", e0);
    lookahead1(4);                  // CommentContents | EOF | '(:' | ':)'
    switch (l1)
    {
    case 55:                        // ':)'
      shift(55);                    // ':)'
      break;
    case 44:                        // '(:'
      shift(44);                    // '(:'
      break;
    case 32:                        // CommentContents
      shift(32);                    // CommentContents
      break;
    default:
      shift(35);                    // EOF
    }
    eventHandler.endNonterminal("Comment", e0);
  };

  this.parse_CommentDoc = function()
  {
    eventHandler.startNonterminal("CommentDoc", e0);
    lookahead1(6);                  // DocTag | DocCommentContents | EOF | '(:' | ':)'
    switch (l1)
    {
    case 33:                        // DocTag
      shift(33);                    // DocTag
      break;
    case 34:                        // DocCommentContents
      shift(34);                    // DocCommentContents
      break;
    case 55:                        // ':)'
      shift(55);                    // ':)'
      break;
    case 44:                        // '(:'
      shift(44);                    // '(:'
      break;
    default:
      shift(35);                    // EOF
    }
    eventHandler.endNonterminal("CommentDoc", e0);
  };

  this.parse_QuotString = function()
  {
    eventHandler.startNonterminal("QuotString", e0);
    lookahead1(5);                  // JSONChar | JSONCharRef | JSONPredefinedCharRef | EOF | '"'
    switch (l1)
    {
    case 3:                         // JSONPredefinedCharRef
      shift(3);                     // JSONPredefinedCharRef
      break;
    case 2:                         // JSONCharRef
      shift(2);                     // JSONCharRef
      break;
    case 1:                         // JSONChar
      shift(1);                     // JSONChar
      break;
    case 37:                        // '"'
      shift(37);                    // '"'
      break;
    default:
      shift(35);                    // EOF
    }
    eventHandler.endNonterminal("QuotString", e0);
  };

  this.parse_AposString = function()
  {
    eventHandler.startNonterminal("AposString", e0);
    lookahead1(7);                  // PredefinedEntityRef | EscapeApos | AposChar | CharRef | EOF | "'"
    switch (l1)
    {
    case 21:                        // PredefinedEntityRef
      shift(21);                    // PredefinedEntityRef
      break;
    case 31:                        // CharRef
      shift(31);                    // CharRef
      break;
    case 23:                        // EscapeApos
      shift(23);                    // EscapeApos
      break;
    case 24:                        // AposChar
      shift(24);                    // AposChar
      break;
    case 41:                        // "'"
      shift(41);                    // "'"
      break;
    default:
      shift(35);                    // EOF
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
    case 80:                        // 'attribute'
      shift(80);                    // 'attribute'
      break;
    case 94:                        // 'comment'
      shift(94);                    // 'comment'
      break;
    case 118:                       // 'document-node'
      shift(118);                   // 'document-node'
      break;
    case 119:                       // 'element'
      shift(119);                   // 'element'
      break;
    case 122:                       // 'empty-sequence'
      shift(122);                   // 'empty-sequence'
      break;
    case 143:                       // 'function'
      shift(143);                   // 'function'
      break;
    case 150:                       // 'if'
      shift(150);                   // 'if'
      break;
    case 163:                       // 'item'
      shift(163);                   // 'item'
      break;
    case 183:                       // 'namespace-node'
      shift(183);                   // 'namespace-node'
      break;
    case 189:                       // 'node'
      shift(189);                   // 'node'
      break;
    case 214:                       // 'processing-instruction'
      shift(214);                   // 'processing-instruction'
      break;
    case 224:                       // 'schema-attribute'
      shift(224);                   // 'schema-attribute'
      break;
    case 225:                       // 'schema-element'
      shift(225);                   // 'schema-element'
      break;
    case 241:                       // 'switch'
      shift(241);                   // 'switch'
      break;
    case 242:                       // 'text'
      shift(242);                   // 'text'
      break;
    case 251:                       // 'typeswitch'
      shift(251);                   // 'typeswitch'
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
    case 17:                        // EQName^Token
      shift(17);                    // EQName^Token
      break;
    case 68:                        // 'after'
      shift(68);                    // 'after'
      break;
    case 71:                        // 'ancestor'
      shift(71);                    // 'ancestor'
      break;
    case 72:                        // 'ancestor-or-self'
      shift(72);                    // 'ancestor-or-self'
      break;
    case 73:                        // 'and'
      shift(73);                    // 'and'
      break;
    case 77:                        // 'as'
      shift(77);                    // 'as'
      break;
    case 78:                        // 'ascending'
      shift(78);                    // 'ascending'
      break;
    case 82:                        // 'before'
      shift(82);                    // 'before'
      break;
    case 86:                        // 'case'
      shift(86);                    // 'case'
      break;
    case 87:                        // 'cast'
      shift(87);                    // 'cast'
      break;
    case 88:                        // 'castable'
      shift(88);                    // 'castable'
      break;
    case 91:                        // 'child'
      shift(91);                    // 'child'
      break;
    case 92:                        // 'collation'
      shift(92);                    // 'collation'
      break;
    case 101:                       // 'copy'
      shift(101);                   // 'copy'
      break;
    case 103:                       // 'count'
      shift(103);                   // 'count'
      break;
    case 106:                       // 'declare'
      shift(106);                   // 'declare'
      break;
    case 107:                       // 'default'
      shift(107);                   // 'default'
      break;
    case 108:                       // 'delete'
      shift(108);                   // 'delete'
      break;
    case 109:                       // 'descendant'
      shift(109);                   // 'descendant'
      break;
    case 110:                       // 'descendant-or-self'
      shift(110);                   // 'descendant-or-self'
      break;
    case 111:                       // 'descending'
      shift(111);                   // 'descending'
      break;
    case 116:                       // 'div'
      shift(116);                   // 'div'
      break;
    case 117:                       // 'document'
      shift(117);                   // 'document'
      break;
    case 120:                       // 'else'
      shift(120);                   // 'else'
      break;
    case 121:                       // 'empty'
      shift(121);                   // 'empty'
      break;
    case 124:                       // 'end'
      shift(124);                   // 'end'
      break;
    case 126:                       // 'eq'
      shift(126);                   // 'eq'
      break;
    case 127:                       // 'every'
      shift(127);                   // 'every'
      break;
    case 129:                       // 'except'
      shift(129);                   // 'except'
      break;
    case 132:                       // 'first'
      shift(132);                   // 'first'
      break;
    case 133:                       // 'following'
      shift(133);                   // 'following'
      break;
    case 134:                       // 'following-sibling'
      shift(134);                   // 'following-sibling'
      break;
    case 135:                       // 'for'
      shift(135);                   // 'for'
      break;
    case 144:                       // 'ge'
      shift(144);                   // 'ge'
      break;
    case 146:                       // 'group'
      shift(146);                   // 'group'
      break;
    case 148:                       // 'gt'
      shift(148);                   // 'gt'
      break;
    case 149:                       // 'idiv'
      shift(149);                   // 'idiv'
      break;
    case 151:                       // 'import'
      shift(151);                   // 'import'
      break;
    case 157:                       // 'insert'
      shift(157);                   // 'insert'
      break;
    case 158:                       // 'instance'
      shift(158);                   // 'instance'
      break;
    case 160:                       // 'intersect'
      shift(160);                   // 'intersect'
      break;
    case 161:                       // 'into'
      shift(161);                   // 'into'
      break;
    case 162:                       // 'is'
      shift(162);                   // 'is'
      break;
    case 168:                       // 'last'
      shift(168);                   // 'last'
      break;
    case 170:                       // 'le'
      shift(170);                   // 'le'
      break;
    case 172:                       // 'let'
      shift(172);                   // 'let'
      break;
    case 176:                       // 'lt'
      shift(176);                   // 'lt'
      break;
    case 178:                       // 'mod'
      shift(178);                   // 'mod'
      break;
    case 179:                       // 'modify'
      shift(179);                   // 'modify'
      break;
    case 180:                       // 'module'
      shift(180);                   // 'module'
      break;
    case 182:                       // 'namespace'
      shift(182);                   // 'namespace'
      break;
    case 184:                       // 'ne'
      shift(184);                   // 'ne'
      break;
    case 196:                       // 'only'
      shift(196);                   // 'only'
      break;
    case 198:                       // 'or'
      shift(198);                   // 'or'
      break;
    case 199:                       // 'order'
      shift(199);                   // 'order'
      break;
    case 200:                       // 'ordered'
      shift(200);                   // 'ordered'
      break;
    case 204:                       // 'parent'
      shift(204);                   // 'parent'
      break;
    case 210:                       // 'preceding'
      shift(210);                   // 'preceding'
      break;
    case 211:                       // 'preceding-sibling'
      shift(211);                   // 'preceding-sibling'
      break;
    case 216:                       // 'rename'
      shift(216);                   // 'rename'
      break;
    case 217:                       // 'replace'
      shift(217);                   // 'replace'
      break;
    case 218:                       // 'return'
      shift(218);                   // 'return'
      break;
    case 222:                       // 'satisfies'
      shift(222);                   // 'satisfies'
      break;
    case 227:                       // 'self'
      shift(227);                   // 'self'
      break;
    case 233:                       // 'some'
      shift(233);                   // 'some'
      break;
    case 234:                       // 'stable'
      shift(234);                   // 'stable'
      break;
    case 235:                       // 'start'
      shift(235);                   // 'start'
      break;
    case 246:                       // 'to'
      shift(246);                   // 'to'
      break;
    case 247:                       // 'treat'
      shift(247);                   // 'treat'
      break;
    case 248:                       // 'try'
      shift(248);                   // 'try'
      break;
    case 252:                       // 'union'
      shift(252);                   // 'union'
      break;
    case 254:                       // 'unordered'
      shift(254);                   // 'unordered'
      break;
    case 258:                       // 'validate'
      shift(258);                   // 'validate'
      break;
    case 264:                       // 'where'
      shift(264);                   // 'where'
      break;
    case 268:                       // 'with'
      shift(268);                   // 'with'
      break;
    case 272:                       // 'xquery'
      shift(272);                   // 'xquery'
      break;
    case 70:                        // 'allowing'
      shift(70);                    // 'allowing'
      break;
    case 79:                        // 'at'
      shift(79);                    // 'at'
      break;
    case 81:                        // 'base-uri'
      shift(81);                    // 'base-uri'
      break;
    case 83:                        // 'boundary-space'
      shift(83);                    // 'boundary-space'
      break;
    case 84:                        // 'break'
      shift(84);                    // 'break'
      break;
    case 89:                        // 'catch'
      shift(89);                    // 'catch'
      break;
    case 96:                        // 'construction'
      shift(96);                    // 'construction'
      break;
    case 99:                        // 'context'
      shift(99);                    // 'context'
      break;
    case 100:                       // 'continue'
      shift(100);                   // 'continue'
      break;
    case 102:                       // 'copy-namespaces'
      shift(102);                   // 'copy-namespaces'
      break;
    case 104:                       // 'decimal-format'
      shift(104);                   // 'decimal-format'
      break;
    case 123:                       // 'encoding'
      shift(123);                   // 'encoding'
      break;
    case 130:                       // 'exit'
      shift(130);                   // 'exit'
      break;
    case 131:                       // 'external'
      shift(131);                   // 'external'
      break;
    case 139:                       // 'ft-option'
      shift(139);                   // 'ft-option'
      break;
    case 152:                       // 'in'
      shift(152);                   // 'in'
      break;
    case 153:                       // 'index'
      shift(153);                   // 'index'
      break;
    case 159:                       // 'integrity'
      shift(159);                   // 'integrity'
      break;
    case 169:                       // 'lax'
      shift(169);                   // 'lax'
      break;
    case 190:                       // 'nodes'
      shift(190);                   // 'nodes'
      break;
    case 197:                       // 'option'
      shift(197);                   // 'option'
      break;
    case 201:                       // 'ordering'
      shift(201);                   // 'ordering'
      break;
    case 220:                       // 'revalidation'
      shift(220);                   // 'revalidation'
      break;
    case 223:                       // 'schema'
      shift(223);                   // 'schema'
      break;
    case 226:                       // 'score'
      shift(226);                   // 'score'
      break;
    case 232:                       // 'sliding'
      shift(232);                   // 'sliding'
      break;
    case 238:                       // 'strict'
      shift(238);                   // 'strict'
      break;
    case 249:                       // 'tumbling'
      shift(249);                   // 'tumbling'
      break;
    case 250:                       // 'type'
      shift(250);                   // 'type'
      break;
    case 255:                       // 'updating'
      shift(255);                   // 'updating'
      break;
    case 259:                       // 'value'
      shift(259);                   // 'value'
      break;
    case 260:                       // 'variable'
      shift(260);                   // 'variable'
      break;
    case 261:                       // 'version'
      shift(261);                   // 'version'
      break;
    case 265:                       // 'while'
      shift(265);                   // 'while'
      break;
    case 95:                        // 'constraint'
      shift(95);                    // 'constraint'
      break;
    case 174:                       // 'loop'
      shift(174);                   // 'loop'
      break;
    default:
      shift(219);                   // 'returning'
    }
    eventHandler.endNonterminal("FunctionName", e0);
  }

  function parse_NCName()
  {
    eventHandler.startNonterminal("NCName", e0);
    switch (l1)
    {
    case 28:                        // NCName^Token
      shift(28);                    // NCName^Token
      break;
    case 68:                        // 'after'
      shift(68);                    // 'after'
      break;
    case 73:                        // 'and'
      shift(73);                    // 'and'
      break;
    case 77:                        // 'as'
      shift(77);                    // 'as'
      break;
    case 78:                        // 'ascending'
      shift(78);                    // 'ascending'
      break;
    case 82:                        // 'before'
      shift(82);                    // 'before'
      break;
    case 86:                        // 'case'
      shift(86);                    // 'case'
      break;
    case 87:                        // 'cast'
      shift(87);                    // 'cast'
      break;
    case 88:                        // 'castable'
      shift(88);                    // 'castable'
      break;
    case 92:                        // 'collation'
      shift(92);                    // 'collation'
      break;
    case 103:                       // 'count'
      shift(103);                   // 'count'
      break;
    case 107:                       // 'default'
      shift(107);                   // 'default'
      break;
    case 111:                       // 'descending'
      shift(111);                   // 'descending'
      break;
    case 116:                       // 'div'
      shift(116);                   // 'div'
      break;
    case 120:                       // 'else'
      shift(120);                   // 'else'
      break;
    case 121:                       // 'empty'
      shift(121);                   // 'empty'
      break;
    case 124:                       // 'end'
      shift(124);                   // 'end'
      break;
    case 126:                       // 'eq'
      shift(126);                   // 'eq'
      break;
    case 129:                       // 'except'
      shift(129);                   // 'except'
      break;
    case 135:                       // 'for'
      shift(135);                   // 'for'
      break;
    case 144:                       // 'ge'
      shift(144);                   // 'ge'
      break;
    case 146:                       // 'group'
      shift(146);                   // 'group'
      break;
    case 148:                       // 'gt'
      shift(148);                   // 'gt'
      break;
    case 149:                       // 'idiv'
      shift(149);                   // 'idiv'
      break;
    case 158:                       // 'instance'
      shift(158);                   // 'instance'
      break;
    case 160:                       // 'intersect'
      shift(160);                   // 'intersect'
      break;
    case 161:                       // 'into'
      shift(161);                   // 'into'
      break;
    case 162:                       // 'is'
      shift(162);                   // 'is'
      break;
    case 170:                       // 'le'
      shift(170);                   // 'le'
      break;
    case 172:                       // 'let'
      shift(172);                   // 'let'
      break;
    case 176:                       // 'lt'
      shift(176);                   // 'lt'
      break;
    case 178:                       // 'mod'
      shift(178);                   // 'mod'
      break;
    case 179:                       // 'modify'
      shift(179);                   // 'modify'
      break;
    case 184:                       // 'ne'
      shift(184);                   // 'ne'
      break;
    case 196:                       // 'only'
      shift(196);                   // 'only'
      break;
    case 198:                       // 'or'
      shift(198);                   // 'or'
      break;
    case 199:                       // 'order'
      shift(199);                   // 'order'
      break;
    case 218:                       // 'return'
      shift(218);                   // 'return'
      break;
    case 222:                       // 'satisfies'
      shift(222);                   // 'satisfies'
      break;
    case 234:                       // 'stable'
      shift(234);                   // 'stable'
      break;
    case 235:                       // 'start'
      shift(235);                   // 'start'
      break;
    case 246:                       // 'to'
      shift(246);                   // 'to'
      break;
    case 247:                       // 'treat'
      shift(247);                   // 'treat'
      break;
    case 252:                       // 'union'
      shift(252);                   // 'union'
      break;
    case 264:                       // 'where'
      shift(264);                   // 'where'
      break;
    case 268:                       // 'with'
      shift(268);                   // 'with'
      break;
    case 71:                        // 'ancestor'
      shift(71);                    // 'ancestor'
      break;
    case 72:                        // 'ancestor-or-self'
      shift(72);                    // 'ancestor-or-self'
      break;
    case 80:                        // 'attribute'
      shift(80);                    // 'attribute'
      break;
    case 91:                        // 'child'
      shift(91);                    // 'child'
      break;
    case 94:                        // 'comment'
      shift(94);                    // 'comment'
      break;
    case 101:                       // 'copy'
      shift(101);                   // 'copy'
      break;
    case 106:                       // 'declare'
      shift(106);                   // 'declare'
      break;
    case 108:                       // 'delete'
      shift(108);                   // 'delete'
      break;
    case 109:                       // 'descendant'
      shift(109);                   // 'descendant'
      break;
    case 110:                       // 'descendant-or-self'
      shift(110);                   // 'descendant-or-self'
      break;
    case 117:                       // 'document'
      shift(117);                   // 'document'
      break;
    case 118:                       // 'document-node'
      shift(118);                   // 'document-node'
      break;
    case 119:                       // 'element'
      shift(119);                   // 'element'
      break;
    case 122:                       // 'empty-sequence'
      shift(122);                   // 'empty-sequence'
      break;
    case 127:                       // 'every'
      shift(127);                   // 'every'
      break;
    case 132:                       // 'first'
      shift(132);                   // 'first'
      break;
    case 133:                       // 'following'
      shift(133);                   // 'following'
      break;
    case 134:                       // 'following-sibling'
      shift(134);                   // 'following-sibling'
      break;
    case 143:                       // 'function'
      shift(143);                   // 'function'
      break;
    case 150:                       // 'if'
      shift(150);                   // 'if'
      break;
    case 151:                       // 'import'
      shift(151);                   // 'import'
      break;
    case 157:                       // 'insert'
      shift(157);                   // 'insert'
      break;
    case 163:                       // 'item'
      shift(163);                   // 'item'
      break;
    case 168:                       // 'last'
      shift(168);                   // 'last'
      break;
    case 180:                       // 'module'
      shift(180);                   // 'module'
      break;
    case 182:                       // 'namespace'
      shift(182);                   // 'namespace'
      break;
    case 183:                       // 'namespace-node'
      shift(183);                   // 'namespace-node'
      break;
    case 189:                       // 'node'
      shift(189);                   // 'node'
      break;
    case 200:                       // 'ordered'
      shift(200);                   // 'ordered'
      break;
    case 204:                       // 'parent'
      shift(204);                   // 'parent'
      break;
    case 210:                       // 'preceding'
      shift(210);                   // 'preceding'
      break;
    case 211:                       // 'preceding-sibling'
      shift(211);                   // 'preceding-sibling'
      break;
    case 214:                       // 'processing-instruction'
      shift(214);                   // 'processing-instruction'
      break;
    case 216:                       // 'rename'
      shift(216);                   // 'rename'
      break;
    case 217:                       // 'replace'
      shift(217);                   // 'replace'
      break;
    case 224:                       // 'schema-attribute'
      shift(224);                   // 'schema-attribute'
      break;
    case 225:                       // 'schema-element'
      shift(225);                   // 'schema-element'
      break;
    case 227:                       // 'self'
      shift(227);                   // 'self'
      break;
    case 233:                       // 'some'
      shift(233);                   // 'some'
      break;
    case 241:                       // 'switch'
      shift(241);                   // 'switch'
      break;
    case 242:                       // 'text'
      shift(242);                   // 'text'
      break;
    case 248:                       // 'try'
      shift(248);                   // 'try'
      break;
    case 251:                       // 'typeswitch'
      shift(251);                   // 'typeswitch'
      break;
    case 254:                       // 'unordered'
      shift(254);                   // 'unordered'
      break;
    case 258:                       // 'validate'
      shift(258);                   // 'validate'
      break;
    case 260:                       // 'variable'
      shift(260);                   // 'variable'
      break;
    case 272:                       // 'xquery'
      shift(272);                   // 'xquery'
      break;
    case 70:                        // 'allowing'
      shift(70);                    // 'allowing'
      break;
    case 79:                        // 'at'
      shift(79);                    // 'at'
      break;
    case 81:                        // 'base-uri'
      shift(81);                    // 'base-uri'
      break;
    case 83:                        // 'boundary-space'
      shift(83);                    // 'boundary-space'
      break;
    case 84:                        // 'break'
      shift(84);                    // 'break'
      break;
    case 89:                        // 'catch'
      shift(89);                    // 'catch'
      break;
    case 96:                        // 'construction'
      shift(96);                    // 'construction'
      break;
    case 99:                        // 'context'
      shift(99);                    // 'context'
      break;
    case 100:                       // 'continue'
      shift(100);                   // 'continue'
      break;
    case 102:                       // 'copy-namespaces'
      shift(102);                   // 'copy-namespaces'
      break;
    case 104:                       // 'decimal-format'
      shift(104);                   // 'decimal-format'
      break;
    case 123:                       // 'encoding'
      shift(123);                   // 'encoding'
      break;
    case 130:                       // 'exit'
      shift(130);                   // 'exit'
      break;
    case 131:                       // 'external'
      shift(131);                   // 'external'
      break;
    case 139:                       // 'ft-option'
      shift(139);                   // 'ft-option'
      break;
    case 152:                       // 'in'
      shift(152);                   // 'in'
      break;
    case 153:                       // 'index'
      shift(153);                   // 'index'
      break;
    case 159:                       // 'integrity'
      shift(159);                   // 'integrity'
      break;
    case 169:                       // 'lax'
      shift(169);                   // 'lax'
      break;
    case 190:                       // 'nodes'
      shift(190);                   // 'nodes'
      break;
    case 197:                       // 'option'
      shift(197);                   // 'option'
      break;
    case 201:                       // 'ordering'
      shift(201);                   // 'ordering'
      break;
    case 220:                       // 'revalidation'
      shift(220);                   // 'revalidation'
      break;
    case 223:                       // 'schema'
      shift(223);                   // 'schema'
      break;
    case 226:                       // 'score'
      shift(226);                   // 'score'
      break;
    case 232:                       // 'sliding'
      shift(232);                   // 'sliding'
      break;
    case 238:                       // 'strict'
      shift(238);                   // 'strict'
      break;
    case 249:                       // 'tumbling'
      shift(249);                   // 'tumbling'
      break;
    case 250:                       // 'type'
      shift(250);                   // 'type'
      break;
    case 255:                       // 'updating'
      shift(255);                   // 'updating'
      break;
    case 259:                       // 'value'
      shift(259);                   // 'value'
      break;
    case 261:                       // 'version'
      shift(261);                   // 'version'
      break;
    case 265:                       // 'while'
      shift(265);                   // 'while'
      break;
    case 95:                        // 'constraint'
      shift(95);                    // 'constraint'
      break;
    case 174:                       // 'loop'
      shift(174);                   // 'loop'
      break;
    default:
      shift(219);                   // 'returning'
    }
    eventHandler.endNonterminal("NCName", e0);
  }

  function shift(t)
  {
    if (l1 == t)
    {
      whitespace();
      eventHandler.terminal(JSONiqTokenizer.TOKEN[l1], b1, e1 > size ? size : e1);
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
      if (code != 30)               // S^WS
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
    var result = JSONiqTokenizer.INITIAL[tokenSetId];
    var state = 0;

    for (var code = result & 4095; code != 0; )
    {
      var charclass;
      var c0 = current < size ? input.charCodeAt(current) : 0;
      ++current;
      if (c0 < 0x80)
      {
        charclass = JSONiqTokenizer.MAP0[c0];
      }
      else if (c0 < 0xd800)
      {
        var c1 = c0 >> 4;
        charclass = JSONiqTokenizer.MAP1[(c0 & 15) + JSONiqTokenizer.MAP1[(c1 & 31) + JSONiqTokenizer.MAP1[c1 >> 5]]];
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
          if (JSONiqTokenizer.MAP2[m] > c0) hi = m - 1;
          else if (JSONiqTokenizer.MAP2[6 + m] < c0) lo = m + 1;
          else {charclass = JSONiqTokenizer.MAP2[12 + m]; break;}
          if (lo > hi) {charclass = 0; break;}
        }
      }

      state = code;
      var i0 = (charclass << 12) + code - 1;
      code = JSONiqTokenizer.TRANSITION[(i0 & 15) + JSONiqTokenizer.TRANSITION[i0 >> 4]];

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

JSONiqTokenizer.getTokenSet = function(tokenSetId)
{
  var set = [];
  var s = tokenSetId < 0 ? - tokenSetId : INITIAL[tokenSetId] & 4095;
  for (var i = 0; i < 279; i += 32)
  {
    var j = i;
    var i0 = (i >> 5) * 2066 + s - 1;
    var i1 = i0 >> 2;
    var i2 = i1 >> 2;
    var f = JSONiqTokenizer.EXPECTED[(i0 & 3) + JSONiqTokenizer.EXPECTED[(i1 & 3) + JSONiqTokenizer.EXPECTED[(i2 & 3) + JSONiqTokenizer.EXPECTED[i2 >> 2]]]];
    for ( ; f != 0; f >>>= 1, ++j)
    {
      if ((f & 1) != 0)
      {
        set.push(JSONiqTokenizer.TOKEN[j]);
      }
    }
  }
  return set;
};

JSONiqTokenizer.MAP0 =
[
  /*   0 */ 67, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 3, 4, 5,
  /*  36 */ 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 18, 18, 18, 18, 18, 18, 18, 18, 18, 19, 20, 21, 22, 23, 24,
  /*  64 */ 25, 26, 27, 28, 29, 30, 27, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 32, 31, 31, 33, 31, 31, 31, 31, 31, 31,
  /*  91 */ 34, 35, 36, 37, 31, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 31, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57,
  /* 118 */ 58, 59, 60, 61, 31, 62, 63, 64, 65, 37
];

JSONiqTokenizer.MAP1 =
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
  /* 231 */ 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 331, 416, 67, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 256 */ 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
  /* 290 */ 15, 16, 17, 18, 18, 18, 18, 18, 18, 18, 18, 18, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 27, 31,
  /* 317 */ 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 37, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31,
  /* 344 */ 31, 31, 31, 31, 32, 31, 31, 33, 31, 31, 31, 31, 31, 31, 34, 35, 36, 37, 31, 37, 38, 39, 40, 41, 42, 43, 44,
  /* 371 */ 45, 46, 31, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 31, 62, 63, 64, 65, 37, 37, 37, 37,
  /* 398 */ 37, 37, 37, 37, 37, 37, 37, 37, 31, 31, 37, 37, 37, 37, 37, 37, 37, 66, 37, 37, 37, 37, 37, 37, 37, 37, 37,
  /* 425 */ 37, 37, 37, 37, 37, 37, 37, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66
];

JSONiqTokenizer.MAP2 =
[
  /*  0 */ 57344, 63744, 64976, 65008, 65536, 983040, 63743, 64975, 65007, 65533, 983039, 1114111, 37, 31, 37, 31, 31,
  /* 17 */ 37
];

JSONiqTokenizer.INITIAL =
[
  /*  0 */ 1, 2, 49155, 57348, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
];

JSONiqTokenizer.TRANSITION =
[
  /*     0 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*    15 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*    30 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*    45 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*    60 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*    75 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*    90 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   105 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   120 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   135 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   150 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   165 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   180 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   195 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   210 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   225 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   240 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   255 */ 19058, 17408, 19288, 17439, 36866, 17466, 36890, 36866, 21991, 22971, 22987, 17556, 17575, 22288, 17486,
  /*   270 */ 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 22126, 17990, 18622, 19411, 20306, 17996, 17689,
  /*   285 */ 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17672, 18921, 19514, 17705,
  /*   300 */ 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008, 19469, 17878,
  /*   315 */ 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102,
  /*   330 */ 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 36919, 18234, 18262, 18278, 18294,
  /*   345 */ 18320, 18336, 18361, 18397, 18419, 18432, 18304, 18448, 18485, 18523, 18553, 18583, 18599, 18638, 18497,
  /*   360 */ 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450,
  /*   375 */ 22022, 18765, 18825, 18841, 18871, 18906, 18944, 18960, 18976, 19041, 19056, 19058, 19058, 19058, 19058,
  /*   390 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   405 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   420 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   435 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   450 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   465 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   480 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   495 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   510 */ 19058, 19058, 19074, 36169, 17439, 36866, 17466, 36890, 36866, 22314, 19105, 22987, 17556, 17575, 22288,
  /*   525 */ 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 22126, 17990, 18622, 19411, 20306, 17996,
  /*   540 */ 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17672, 18921, 19514,
  /*   555 */ 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008, 19469,
  /*   570 */ 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928,
  /*   585 */ 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 36919, 18234, 18262, 18278,
  /*   600 */ 18294, 18320, 18336, 18361, 18397, 18419, 18432, 18304, 18448, 18485, 18523, 18553, 18583, 18599, 18638,
  /*   615 */ 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838,
  /*   630 */ 17450, 22022, 18765, 18825, 18841, 18871, 18906, 18944, 18960, 18976, 19041, 19056, 19058, 19058, 19058,
  /*   645 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   660 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   675 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   690 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   705 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   720 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   735 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   750 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   765 */ 19058, 19058, 19058, 22182, 19288, 19121, 36866, 17466, 18345, 36866, 21991, 22971, 22987, 17556, 17575,
  /*   780 */ 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411, 20306,
  /*   795 */ 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17862, 18921,
  /*   810 */ 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008,
  /*   825 */ 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906,
  /*   840 */ 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935, 18262,
  /*   855 */ 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583, 19149,
  /*   870 */ 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054,
  /*   885 */ 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058, 19058,
  /*   900 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   915 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   930 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   945 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   960 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   975 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*   990 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1005 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1020 */ 19058, 19058, 19058, 19058, 19273, 19552, 19304, 36866, 17466, 36890, 36866, 21991, 22971, 22987, 17556,
  /*  1035 */ 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411,
  /*  1050 */ 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17862,
  /*  1065 */ 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712,
  /*  1080 */ 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890,
  /*  1095 */ 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935,
  /*  1110 */ 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583,
  /*  1125 */ 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915,
  /*  1140 */ 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058,
  /*  1155 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1170 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1185 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1200 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1215 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1230 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1245 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1260 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1275 */ 19058, 19058, 19058, 19058, 19058, 19332, 17423, 19363, 36866, 17466, 17537, 36866, 21991, 22971, 22987,
  /*  1290 */ 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 18614, 18622,
  /*  1305 */ 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 19391, 36867, 19404, 20299, 36866, 17647,
  /*  1320 */ 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 19427, 18403, 18928, 19521,
  /*  1335 */ 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884,
  /*  1350 */ 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134,
  /*  1365 */ 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553,
  /*  1380 */ 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906,
  /*  1395 */ 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056,
  /*  1410 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1425 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1440 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1455 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1470 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1485 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1500 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1515 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1530 */ 19058, 19058, 19058, 19058, 19058, 19058, 36154, 19288, 19457, 36866, 17466, 17740, 36866, 21991, 22971,
  /*  1545 */ 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990,
  /*  1560 */ 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866,
  /*  1575 */ 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928,
  /*  1590 */ 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218,
  /*  1605 */ 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026,
  /*  1620 */ 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523,
  /*  1635 */ 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026,
  /*  1650 */ 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041,
  /*  1665 */ 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1680 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1695 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1710 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1725 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1740 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1755 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1770 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1785 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 22780, 19288, 19457, 36866, 17466, 36890, 36866, 21991,
  /*  1800 */ 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462,
  /*  1815 */ 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299,
  /*  1830 */ 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403,
  /*  1845 */ 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064,
  /*  1860 */ 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010,
  /*  1875 */ 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485,
  /*  1890 */ 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681,
  /*  1905 */ 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976,
  /*  1920 */ 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1935 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1950 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1965 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1980 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  1995 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2010 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2025 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2040 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 22375, 22197, 18469, 36866, 17466, 36890, 36866,
  /*  2055 */ 21991, 24018, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 21331, 22984, 17553, 17572, 22285,
  /*  2070 */ 18462, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 19485, 19501, 36867, 19404,
  /*  2085 */ 20299, 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854,
  /*  2100 */ 18403, 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381,
  /*  2115 */ 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214,
  /*  2130 */ 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448,
  /*  2145 */ 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737,
  /*  2160 */ 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257,
  /*  2175 */ 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2190 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2205 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2220 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2235 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2250 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2265 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2280 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2295 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19537, 22390, 19568, 36866, 17466, 36890,
  /*  2310 */ 36866, 21991, 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572,
  /*  2325 */ 22285, 18462, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867,
  /*  2340 */ 19404, 20299, 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825,
  /*  2355 */ 17854, 18403, 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012,
  /*  2370 */ 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166,
  /*  2385 */ 18214, 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304,
  /*  2400 */ 18448, 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712,
  /*  2415 */ 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241,
  /*  2430 */ 19257, 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2445 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2460 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2475 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2490 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2505 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2520 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2535 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2550 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19596, 19611, 19457, 36866, 17466,
  /*  2565 */ 36890, 36866, 18246, 19627, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553,
  /*  2580 */ 17572, 22285, 18462, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083,
  /*  2595 */ 36867, 19404, 20299, 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800,
  /*  2610 */ 17825, 17854, 18403, 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960,
  /*  2625 */ 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150,
  /*  2640 */ 18166, 18214, 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096,
  /*  2655 */ 18304, 18448, 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164,
  /*  2670 */ 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906,
  /*  2685 */ 19241, 19257, 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2700 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2715 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2730 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2745 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2760 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2775 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2790 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2805 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 22242, 20553, 19457, 36866,
  /*  2820 */ 17466, 36890, 36866, 18648, 30477, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984,
  /*  2835 */ 17553, 17572, 22285, 18462, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619,
  /*  2850 */ 22083, 36867, 19404, 20299, 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784,
  /*  2865 */ 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178,
  /*  2880 */ 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493,
  /*  2895 */ 18150, 18166, 18214, 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274,
  /*  2910 */ 22096, 18304, 18448, 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696,
  /*  2925 */ 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871,
  /*  2940 */ 18906, 19241, 19257, 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2955 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2970 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  2985 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3000 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3015 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3030 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3045 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3060 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36472, 19288, 19457,
  /*  3075 */ 36866, 17466, 17809, 36866, 21991, 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 21770,
  /*  3090 */ 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468,
  /*  3105 */ 17619, 19643, 36867, 19404, 20299, 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756,
  /*  3120 */ 17784, 17800, 17825, 19672, 18403, 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944,
  /*  3135 */ 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963,
  /*  3150 */ 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397,
  /*  3165 */ 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507,
  /*  3180 */ 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841,
  /*  3195 */ 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3210 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3225 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3240 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3255 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3270 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3285 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3300 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3315 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 20538, 19288,
  /*  3330 */ 19457, 36866, 17466, 36890, 36866, 21991, 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373,
  /*  3345 */ 17975, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896,
  /*  3360 */ 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728,
  /*  3375 */ 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922,
  /*  3390 */ 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931,
  /*  3405 */ 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361,
  /*  3420 */ 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680,
  /*  3435 */ 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225,
  /*  3450 */ 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3465 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3480 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3495 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3510 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3525 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3540 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3555 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3570 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 22345,
  /*  3585 */ 19288, 19457, 36866, 17466, 36890, 36866, 21991, 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525,
  /*  3600 */ 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591,
  /*  3615 */ 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017,
  /*  3630 */ 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900,
  /*  3645 */ 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130,
  /*  3660 */ 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336,
  /*  3675 */ 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664,
  /*  3690 */ 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765,
  /*  3705 */ 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3720 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3735 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3750 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3765 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3780 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3795 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3810 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3825 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3840 */ 19726, 19742, 21529, 24035, 23112, 26225, 23511, 27749, 27397, 24035, 34360, 24035, 24036, 23114, 35166,
  /*  3855 */ 23114, 23114, 19758, 23511, 35247, 23511, 23511, 28447, 19803, 24035, 24035, 24035, 24035, 26576, 23114,
  /*  3870 */ 23114, 23114, 23114, 24254, 19821, 23511, 23511, 23511, 23511, 23512, 19441, 36539, 24035, 24035, 24035,
  /*  3885 */ 24035, 19846, 19869, 23114, 23114, 23114, 28618, 32187, 19892, 23511, 23511, 23511, 34585, 20402, 36647,
  /*  3900 */ 24035, 24035, 24036, 23114, 33757, 23114, 23114, 23029, 20271, 23511, 27070, 23511, 23511, 30562, 24035,
  /*  3915 */ 24035, 29274, 26576, 23114, 23114, 31118, 23036, 29695, 23511, 23511, 32431, 23634, 30821, 24035, 23110,
  /*  3930 */ 19913, 23114, 23467, 31261, 23261, 34299, 19932, 24035, 32609, 19965, 35389, 19984, 27689, 19830, 29391,
  /*  3945 */ 29337, 20041, 22643, 35619, 33728, 20062, 20121, 20166, 35100, 26145, 20211, 23008, 19876, 20208, 20227,
  /*  3960 */ 25670, 20132, 26578, 27685, 20141, 20243, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058,
  /*  3975 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  3990 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4005 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4020 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4035 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4050 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4065 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4080 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4095 */ 19058, 36094, 19288, 19457, 36866, 17466, 21724, 36866, 21991, 22971, 22987, 17556, 17575, 22288, 17486,
  /*  4110 */ 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411, 20306, 17996, 17689,
  /*  4125 */ 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17862, 18921, 19514, 17705,
  /*  4140 */ 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008, 37024, 17878,
  /*  4155 */ 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102,
  /*  4170 */ 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935, 18262, 18278, 18294,
  /*  4185 */ 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583, 19149, 18638, 18497,
  /*  4200 */ 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450,
  /*  4215 */ 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058, 19058, 19058, 19058,
  /*  4230 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4245 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4260 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4275 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4290 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4305 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4320 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4335 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4350 */ 19058, 19058, 22735, 19552, 20287, 36866, 17466, 36890, 36866, 21991, 22971, 22987, 17556, 17575, 22288,
  /*  4365 */ 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411, 20306, 17996,
  /*  4380 */ 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17862, 18921, 19514,
  /*  4395 */ 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008, 37024,
  /*  4410 */ 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928,
  /*  4425 */ 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935, 18262, 18278,
  /*  4440 */ 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583, 19149, 18638,
  /*  4455 */ 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838,
  /*  4470 */ 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058, 19058, 19058,
  /*  4485 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4500 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4515 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4530 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4545 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4560 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4575 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4590 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4605 */ 19058, 19058, 19058, 22750, 19288, 21529, 24035, 23112, 28056, 23511, 29483, 28756, 24035, 24035, 24035,
  /*  4620 */ 24036, 23114, 23114, 23114, 23114, 20327, 23511, 23511, 23511, 23511, 31156, 19803, 24035, 24035, 24035,
  /*  4635 */ 24035, 26576, 23114, 23114, 23114, 23114, 24254, 20371, 23511, 23511, 23511, 23511, 27443, 20395, 24035,
  /*  4650 */ 24035, 24035, 24035, 24035, 23113, 23114, 23114, 23114, 23114, 29457, 29700, 23511, 23511, 23511, 23511,
  /*  4665 */ 33444, 20402, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 28350, 20421, 23511, 23511, 23511,
  /*  4680 */ 23511, 25645, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 20447, 20475, 23511, 23511, 23511, 23634,
  /*  4695 */ 24035, 24035, 23110, 23114, 23114, 20499, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078,
  /*  4710 */ 27689, 19830, 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008,
  /*  4725 */ 19876, 20208, 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058,
  /*  4740 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4755 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4770 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4785 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4800 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4815 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4830 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4845 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  4860 */ 19058, 19058, 19058, 19058, 20523, 22257, 20569, 20783, 21715, 17603, 20699, 20837, 20614, 20630, 21149,
  /*  4875 */ 20670, 21405, 17486, 17509, 17525, 18373, 19179, 20695, 20716, 20732, 20755, 19194, 18042, 21641, 20592,
  /*  4890 */ 20779, 20598, 21412, 17470, 17591, 20896, 17468, 17619, 20799, 20700, 21031, 20744, 20699, 20828, 18075,
  /*  4905 */ 21259, 20581, 20853, 18048, 20868, 20884, 17756, 17784, 17800, 17825, 17854, 21171, 21200, 20931, 20947,
  /*  4920 */ 21378, 20955, 20971, 18086, 20645, 21002, 20986, 18178, 17960, 18012, 18381, 18064, 29176, 21044, 21438,
  /*  4935 */ 21018, 21122, 21393, 21060, 21844, 21094, 20654, 17493, 18150, 18166, 18214, 25967, 20763, 21799, 21110,
  /*  4950 */ 21830, 21138, 21246, 21301, 18336, 18361, 21165, 21187, 20812, 21216, 21232, 21287, 21317, 18553, 21347,
  /*  4965 */ 21363, 21428, 21454, 21271, 21483, 21499, 21515, 21575, 21467, 18712, 21591, 21633, 21078, 18189, 18198,
  /*  4980 */ 20679, 21657, 21701, 21074, 21687, 21740, 21756, 21786, 21815, 21860, 21876, 21892, 21946, 21962, 19058,
  /*  4995 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5010 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5025 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5040 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5055 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5070 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5085 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5100 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5115 */ 19058, 19058, 19058, 19058, 19058, 36457, 19288, 19457, 36866, 17466, 36890, 36866, 21991, 22971, 22987,
  /*  5130 */ 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 36813, 17990, 18622,
  /*  5145 */ 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647,
  /*  5160 */ 21981, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521,
  /*  5175 */ 17712, 37008, 22151, 22007, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 27898, 17884,
  /*  5190 */ 18890, 17906, 17928, 22042, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 22070, 22112, 25026, 18134,
  /*  5205 */ 36935, 18262, 18278, 18294, 18320, 18336, 18361, 22142, 18274, 22096, 18304, 18448, 18485, 18523, 18553,
  /*  5220 */ 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906,
  /*  5235 */ 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056,
  /*  5250 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5265 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5280 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5295 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5310 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5325 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5340 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5355 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5370 */ 19058, 19058, 19058, 19058, 19058, 19058, 36109, 19288, 18469, 36866, 17466, 36890, 36866, 21991, 22971,
  /*  5385 */ 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990,
  /*  5400 */ 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866,
  /*  5415 */ 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928,
  /*  5430 */ 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218,
  /*  5445 */ 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026,
  /*  5460 */ 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523,
  /*  5475 */ 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026,
  /*  5490 */ 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041,
  /*  5505 */ 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5520 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5535 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5550 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5565 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5580 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5595 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5610 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5625 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 22167, 19288, 19457, 36866, 17466, 17768, 36866, 21991,
  /*  5640 */ 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462,
  /*  5655 */ 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299,
  /*  5670 */ 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403,
  /*  5685 */ 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064,
  /*  5700 */ 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010,
  /*  5715 */ 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485,
  /*  5730 */ 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681,
  /*  5745 */ 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976,
  /*  5760 */ 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5775 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5790 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5805 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5820 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5835 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5850 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5865 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  5880 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 22227, 36487, 22273, 36866, 17466, 36890, 36866,
  /*  5895 */ 19316, 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285,
  /*  5910 */ 18749, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404,
  /*  5925 */ 20299, 36866, 17647, 22304, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854,
  /*  5940 */ 18403, 18928, 19521, 17712, 37008, 19580, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381,
  /*  5955 */ 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214,
  /*  5970 */ 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448,
  /*  5985 */ 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737,
  /*  6000 */ 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257,
  /*  6015 */ 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6030 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6045 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6060 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6075 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6090 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6105 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6120 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6135 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 22330, 19089, 19457, 36866, 17466, 18721,
  /*  6150 */ 36866, 21991, 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572,
  /*  6165 */ 22285, 18462, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867,
  /*  6180 */ 19404, 20299, 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825,
  /*  6195 */ 17854, 18403, 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012,
  /*  6210 */ 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166,
  /*  6225 */ 18214, 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304,
  /*  6240 */ 18448, 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712,
  /*  6255 */ 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241,
  /*  6270 */ 19257, 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6285 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6300 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6315 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6330 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6345 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6360 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6375 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6390 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 22765, 19347, 19457, 36866, 17466,
  /*  6405 */ 36890, 36866, 18114, 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553,
  /*  6420 */ 17572, 22285, 18462, 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083,
  /*  6435 */ 36867, 19404, 20299, 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800,
  /*  6450 */ 17825, 17854, 18403, 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960,
  /*  6465 */ 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150,
  /*  6480 */ 18166, 18214, 25010, 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096,
  /*  6495 */ 18304, 18448, 18485, 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164,
  /*  6510 */ 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906,
  /*  6525 */ 19241, 19257, 18976, 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6540 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6555 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6570 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6585 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6600 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6615 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6630 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6645 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36079, 19288, 21605, 24035,
  /*  6660 */ 23112, 32618, 23511, 29483, 29939, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 22420, 23511,
  /*  6675 */ 23511, 23511, 23511, 29116, 19803, 24035, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23114, 33811,
  /*  6690 */ 22468, 23511, 23511, 23511, 23511, 27443, 22493, 24035, 24035, 24035, 24035, 24035, 23113, 23114, 23114,
  /*  6705 */ 23114, 23114, 28618, 29700, 23511, 23511, 23511, 23511, 34541, 20402, 24035, 24035, 24035, 24036, 23114,
  /*  6720 */ 23114, 23114, 23114, 23029, 22839, 23511, 23511, 23511, 23511, 25645, 24035, 24035, 24035, 26576, 23114,
  /*  6735 */ 23114, 23114, 32683, 22516, 23511, 23511, 23511, 22540, 24035, 24035, 23110, 23114, 23114, 20499, 23511,
  /*  6750 */ 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035, 23112, 19872, 27741, 23266,
  /*  6765 */ 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007, 20046, 20132, 26578, 27685,
  /*  6780 */ 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6795 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6810 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6825 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6840 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6855 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6870 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6885 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  6900 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36079, 19288, 21605,
  /*  6915 */ 24035, 23112, 32618, 23511, 29483, 29939, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 22420,
  /*  6930 */ 23511, 23511, 23511, 23511, 29116, 19803, 24035, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23114,
  /*  6945 */ 33811, 22468, 23511, 23511, 23511, 23511, 27443, 22493, 24035, 24035, 24035, 24035, 24035, 23113, 23114,
  /*  6960 */ 23114, 23114, 23114, 28618, 29700, 23511, 23511, 23511, 23511, 34564, 20402, 24035, 24035, 24035, 24036,
  /*  6975 */ 23114, 23114, 23114, 23114, 23029, 22839, 23511, 23511, 23511, 23511, 25645, 24035, 24035, 24035, 26576,
  /*  6990 */ 23114, 23114, 23114, 32683, 22516, 23511, 23511, 23511, 23634, 24035, 24035, 23110, 23114, 23114, 20499,
  /*  7005 */ 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035, 23112, 19872, 27741,
  /*  7020 */ 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007, 20046, 20132, 26578,
  /*  7035 */ 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7050 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7065 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7080 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7095 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7110 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7125 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7140 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7155 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36079, 19288,
  /*  7170 */ 21605, 24035, 23112, 32618, 23511, 29483, 29939, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114,
  /*  7185 */ 22420, 23511, 23511, 23511, 23511, 29908, 19803, 24035, 24035, 24035, 24035, 26576, 23114, 23114, 23114,
  /*  7200 */ 23114, 33811, 22468, 23511, 23511, 23511, 23511, 27443, 22493, 24035, 24035, 24035, 24035, 24035, 23113,
  /*  7215 */ 23114, 23114, 23114, 23114, 28618, 29700, 23511, 23511, 23511, 23511, 34564, 20402, 24035, 24035, 24035,
  /*  7230 */ 24036, 23114, 23114, 23114, 23114, 23029, 22839, 23511, 23511, 23511, 23511, 25645, 24035, 24035, 24035,
  /*  7245 */ 26576, 23114, 23114, 23114, 32683, 22516, 23511, 23511, 23511, 23634, 24035, 24035, 23110, 23114, 23114,
  /*  7260 */ 20499, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035, 23112, 19872,
  /*  7275 */ 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007, 20046, 20132,
  /*  7290 */ 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7305 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7320 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7335 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7350 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7365 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7380 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7395 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7410 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36079,
  /*  7425 */ 19288, 21605, 24035, 23112, 32618, 23511, 29483, 29939, 24035, 24035, 24035, 24036, 23114, 23114, 23114,
  /*  7440 */ 23114, 22420, 23511, 23511, 23511, 23511, 29116, 19803, 24035, 24035, 24035, 24035, 26576, 23114, 23114,
  /*  7455 */ 23114, 23114, 33811, 22468, 23511, 23511, 23511, 23511, 27443, 22561, 24035, 24035, 24035, 24035, 24035,
  /*  7470 */ 23113, 23114, 23114, 23114, 23114, 28618, 29700, 23511, 23511, 23511, 23511, 34564, 20402, 24035, 24035,
  /*  7485 */ 24035, 24036, 23114, 23114, 23114, 23114, 23029, 22839, 23511, 23511, 23511, 23511, 25645, 24035, 24035,
  /*  7500 */ 24035, 26576, 23114, 23114, 23114, 32683, 22516, 23511, 23511, 23511, 23634, 24035, 24035, 23110, 23114,
  /*  7515 */ 23114, 20499, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035, 23112,
  /*  7530 */ 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007, 20046,
  /*  7545 */ 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7560 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7575 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7590 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7605 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7620 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7635 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7650 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7665 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7680 */ 36079, 19288, 21605, 24035, 23112, 23837, 23511, 29483, 29939, 24035, 24035, 24035, 24036, 23114, 23114,
  /*  7695 */ 23114, 23114, 22584, 23511, 23511, 23511, 23511, 29116, 19803, 24035, 24035, 24035, 24035, 26576, 23114,
  /*  7710 */ 23114, 23114, 23114, 33811, 22468, 23511, 23511, 23511, 23511, 27443, 22493, 24035, 24035, 24035, 24035,
  /*  7725 */ 24035, 23113, 23114, 23114, 23114, 23114, 28618, 29700, 23511, 23511, 23511, 23511, 34564, 20402, 24035,
  /*  7740 */ 24035, 24035, 24036, 23114, 23114, 23114, 23114, 23029, 22839, 23511, 23511, 23511, 23511, 25645, 24035,
  /*  7755 */ 24035, 24035, 26576, 23114, 23114, 23114, 32683, 22516, 23511, 23511, 23511, 23634, 24035, 24035, 23110,
  /*  7770 */ 23114, 23114, 20499, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035,
  /*  7785 */ 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007,
  /*  7800 */ 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058,
  /*  7815 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7830 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7845 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7860 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7875 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7890 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7905 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7920 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  7935 */ 19058, 36079, 19288, 21605, 24035, 23112, 32618, 23511, 31507, 29939, 24035, 24035, 24035, 24036, 23114,
  /*  7950 */ 23114, 23114, 23114, 22420, 23511, 23511, 23511, 23511, 28306, 19803, 24035, 24035, 24035, 24035, 26576,
  /*  7965 */ 23114, 23114, 23114, 23114, 33811, 22468, 23511, 23511, 23511, 23511, 23512, 24694, 24035, 24035, 24035,
  /*  7980 */ 24035, 24035, 23113, 23114, 23114, 23114, 23114, 28618, 29700, 23511, 23511, 23511, 23511, 34585, 20402,
  /*  7995 */ 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 23029, 20271, 23511, 23511, 23511, 23511, 30562,
  /*  8010 */ 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511, 23634, 24035, 24035,
  /*  8025 */ 23110, 23114, 23114, 23467, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830,
  /*  8040 */ 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208,
  /*  8055 */ 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058,
  /*  8070 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8085 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8100 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8115 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8130 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8145 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8160 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8175 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8190 */ 19058, 19058, 36442, 19288, 21605, 24035, 23112, 28137, 23511, 31507, 29939, 24035, 24035, 24035, 24036,
  /*  8205 */ 23114, 23114, 23114, 23114, 22420, 23511, 23511, 23511, 23511, 28306, 19803, 24035, 24035, 24035, 24035,
  /*  8220 */ 26576, 23114, 23114, 23114, 23114, 33811, 22468, 23511, 23511, 23511, 23511, 23512, 24694, 24035, 24035,
  /*  8235 */ 24035, 24035, 24035, 23113, 23114, 23114, 23114, 23114, 28618, 29700, 23511, 23511, 23511, 23511, 34585,
  /*  8250 */ 20402, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 23029, 20271, 23511, 23511, 23511, 23511,
  /*  8265 */ 30562, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511, 23634, 24035,
  /*  8280 */ 24035, 23110, 23114, 23114, 23467, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689,
  /*  8295 */ 19830, 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876,
  /*  8310 */ 20208, 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058,
  /*  8325 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8340 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8355 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8370 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8385 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8400 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8415 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8430 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8445 */ 19058, 19058, 19058, 36079, 19288, 21605, 24035, 23112, 32618, 23511, 31507, 29939, 24035, 24035, 24035,
  /*  8460 */ 24036, 23114, 23114, 23114, 23114, 22420, 23511, 23511, 23511, 23511, 28306, 19803, 24035, 24035, 24035,
  /*  8475 */ 24035, 26576, 23114, 23114, 23114, 23114, 33811, 22468, 23511, 23511, 23511, 23511, 23512, 24694, 24035,
  /*  8490 */ 24035, 24035, 24035, 24035, 23113, 23114, 23114, 23114, 23114, 28618, 29700, 23511, 23511, 23511, 23511,
  /*  8505 */ 34585, 20402, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 23029, 20271, 23511, 23511, 23511,
  /*  8520 */ 23511, 31568, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511, 23634,
  /*  8535 */ 24035, 24035, 23110, 23114, 23114, 23467, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078,
  /*  8550 */ 27689, 19830, 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008,
  /*  8565 */ 19876, 20208, 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058,
  /*  8580 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8595 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8610 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8625 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8640 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8655 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8670 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8685 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8700 */ 19058, 19058, 19058, 19058, 22690, 19288, 19457, 36866, 17466, 36890, 36866, 21991, 27584, 22987, 17556,
  /*  8715 */ 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411,
  /*  8730 */ 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17862,
  /*  8745 */ 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712,
  /*  8760 */ 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890,
  /*  8775 */ 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935,
  /*  8790 */ 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 22659, 18448, 18485, 18523, 18553, 18583,
  /*  8805 */ 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915,
  /*  8820 */ 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058,
  /*  8835 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8850 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8865 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8880 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8895 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8910 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8925 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8940 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  8955 */ 19058, 19058, 19058, 19058, 19058, 22360, 19552, 19457, 36866, 17466, 36890, 36866, 21991, 22971, 22987,
  /*  8970 */ 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990, 18622,
  /*  8985 */ 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647,
  /*  9000 */ 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521,
  /*  9015 */ 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884,
  /*  9030 */ 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134,
  /*  9045 */ 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553,
  /*  9060 */ 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906,
  /*  9075 */ 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056,
  /*  9090 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9105 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9120 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9135 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9150 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9165 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9180 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9195 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9210 */ 19058, 19058, 19058, 19058, 19058, 19058, 22675, 22811, 19457, 36866, 17466, 36890, 36866, 19133, 22971,
  /*  9225 */ 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 22827, 17990,
  /*  9240 */ 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866,
  /*  9255 */ 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928,
  /*  9270 */ 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218,
  /*  9285 */ 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026,
  /*  9300 */ 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523,
  /*  9315 */ 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026,
  /*  9330 */ 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041,
  /*  9345 */ 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9360 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9375 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9390 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9405 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9420 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9435 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9450 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9465 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36139, 19288, 19457, 36866, 17466, 36890, 36866, 21991,
  /*  9480 */ 22971, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462,
  /*  9495 */ 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299,
  /*  9510 */ 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403,
  /*  9525 */ 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064,
  /*  9540 */ 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010,
  /*  9555 */ 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485,
  /*  9570 */ 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681,
  /*  9585 */ 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976,
  /*  9600 */ 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9615 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9630 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9645 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9660 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9675 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9690 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9705 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9720 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36064, 19288, 22865, 22881, 32031, 22897, 22913,
  /*  9735 */ 22956, 29939, 24035, 24035, 24035, 23003, 23114, 23114, 23114, 23024, 22420, 23511, 23511, 23511, 23052,
  /*  9750 */ 29116, 23073, 29268, 24035, 25563, 26915, 23106, 23131, 23114, 23114, 23159, 23181, 23197, 23248, 23511,
  /*  9765 */ 23511, 23282, 23305, 22493, 32364, 24035, 33472, 30138, 26325, 31770, 33508, 27345, 33667, 23114, 23321,
  /*  9780 */ 23473, 23351, 35793, 36576, 23511, 23375, 22500, 24145, 24035, 29197, 20192, 24533, 23440, 23114, 19017,
  /*  9795 */ 23459, 22839, 23489, 23510, 23511, 33563, 23528, 32076, 25389, 24035, 26576, 23561, 23583, 23114, 32683,
  /*  9810 */ 22516, 23622, 23655, 23511, 23634, 35456, 37144, 23110, 23683, 34153, 20499, 32513, 25824, 23705, 24035,
  /*  9825 */ 24035, 23111, 23114, 19874, 27078, 33263, 19830, 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243,
  /*  9840 */ 20507, 32241, 20150, 31862, 27464, 35108, 23727, 23007, 35895, 34953, 26578, 27685, 20141, 24569, 31691,
  /*  9855 */ 19787, 33967, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9870 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9885 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9900 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9915 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9930 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9945 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9960 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /*  9975 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36427, 19552, 21605, 24035, 23112, 32618,
  /*  9990 */ 23511, 29483, 29939, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 22420, 23511, 23511, 23511,
  /* 10005 */ 23511, 29116, 19803, 24035, 24035, 24035, 27027, 26576, 23114, 23114, 23114, 31471, 23756, 22468, 23511,
  /* 10020 */ 23511, 23511, 34687, 23772, 22493, 24035, 24035, 24035, 24035, 24035, 23113, 23114, 23114, 23114, 23114,
  /* 10035 */ 28618, 29700, 23511, 23511, 23511, 23511, 34564, 23788, 24035, 24035, 24035, 21559, 23828, 23114, 23114,
  /* 10050 */ 23114, 25086, 22839, 23853, 23511, 23511, 23511, 23876, 24035, 24035, 24035, 26576, 23114, 23114, 23114,
  /* 10065 */ 32683, 22516, 23511, 23511, 23511, 23634, 24035, 24035, 23110, 23114, 23114, 20499, 23511, 23261, 23628,
  /* 10080 */ 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035, 23112, 19872, 27741, 23266, 24036, 23114,
  /* 10095 */ 30243, 19829, 26577, 26597, 20211, 31761, 23909, 23953, 23007, 20046, 20132, 26578, 27685, 20141, 24569,
  /* 10110 */ 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10125 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10140 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10155 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10170 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10185 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10200 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10215 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10230 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36049, 19288, 21605, 30825, 23112,
  /* 10245 */ 23987, 23511, 24003, 31001, 27617, 24034, 24035, 24036, 24052, 24089, 23114, 23114, 22420, 24109, 24168,
  /* 10260 */ 23511, 23511, 29116, 24188, 27609, 20017, 29516, 24035, 26576, 24222, 19968, 23114, 24252, 33811, 22468,
  /* 10275 */ 24270, 33587, 23511, 24320, 27443, 22493, 24035, 24035, 24035, 24035, 24339, 23113, 23114, 23114, 23114,
  /* 10290 */ 28128, 28618, 29700, 23511, 23511, 23511, 28276, 34564, 20402, 24035, 24035, 32929, 24036, 23114, 23114,
  /* 10305 */ 23114, 24357, 23029, 22839, 23511, 23511, 23511, 24377, 25645, 24035, 34112, 24035, 26576, 23114, 26643,
  /* 10320 */ 23114, 32683, 22516, 23511, 25638, 23511, 23711, 24035, 24395, 27809, 23114, 24414, 20499, 24432, 30917,
  /* 10335 */ 23628, 24035, 30680, 23111, 23114, 30233, 27078, 25748, 24452, 24035, 23112, 19872, 27741, 23266, 24036,
  /* 10350 */ 23114, 24475, 19829, 26577, 26597, 26154, 24519, 24556, 24596, 23007, 20046, 20132, 26578, 24634, 20141,
  /* 10365 */ 24569, 31691, 24679, 24727, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10380 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10395 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10410 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10425 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10440 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10455 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10470 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10485 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36412, 19288, 21605, 19943,
  /* 10500 */ 34861, 32618, 26027, 29483, 32016, 32050, 36233, 24776, 35574, 24801, 24819, 32671, 31289, 22420, 24868,
  /* 10515 */ 24886, 20087, 26849, 29116, 19803, 24035, 24035, 24035, 36228, 26576, 23114, 23114, 23114, 24981, 33811,
  /* 10530 */ 22468, 23511, 23511, 23511, 29028, 27443, 22493, 24923, 27965, 24035, 24035, 32797, 24946, 23443, 23114,
  /* 10545 */ 23114, 29636, 24997, 22849, 28252, 23511, 23511, 23511, 25042, 25110, 24035, 24035, 34085, 24036, 25133,
  /* 10560 */ 23114, 23114, 25152, 23029, 22839, 25169, 23511, 36764, 23511, 25645, 30403, 24035, 25186, 26576, 31806,
  /* 10575 */ 24093, 25212, 32683, 22516, 32713, 26245, 34293, 23634, 24035, 24035, 23110, 23114, 23114, 20499, 23511,
  /* 10590 */ 23261, 23628, 24035, 32406, 23111, 23114, 28676, 30944, 27689, 25234, 24035, 23112, 19872, 37063, 23266,
  /* 10605 */ 24036, 23114, 30243, 20379, 26100, 29218, 20211, 30105, 25257, 25284, 23007, 20046, 20132, 26578, 27685,
  /* 10620 */ 20141, 24569, 24834, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10635 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10650 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10665 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10680 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10695 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10710 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10725 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10740 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36034, 19288, 21671,
  /* 10755 */ 25314, 25072, 25330, 25346, 25362, 29939, 29951, 35288, 29984, 23812, 27216, 25405, 25424, 30456, 22584,
  /* 10770 */ 26292, 25461, 25480, 31592, 29116, 25516, 34963, 25545, 27007, 25579, 33937, 25614, 25661, 25686, 34872,
  /* 10785 */ 25702, 25718, 25734, 25769, 25795, 25811, 25840, 22493, 26533, 25856, 24035, 25876, 30763, 27481, 25909,
  /* 10800 */ 23114, 28987, 25936, 25954, 29700, 25983, 23511, 31412, 26043, 26063, 22568, 29241, 29592, 26116, 31216,
  /* 10815 */ 35383, 26170, 34783, 26194, 26221, 22839, 26241, 26261, 22477, 26283, 26308, 27306, 31035, 24655, 26576,
  /* 10830 */ 29854, 33386, 26341, 32683, 22516, 32153, 30926, 26361, 19996, 26381, 35463, 26397, 26424, 34646, 26478,
  /* 10845 */ 35605, 31386, 26494, 35567, 31964, 22940, 23689, 25218, 30309, 32289, 19830, 33605, 23112, 32109, 27733,
  /* 10860 */ 27084, 24496, 35886, 35221, 26525, 36602, 26549, 26558, 26574, 26594, 26613, 26629, 26666, 26700, 26578,
  /* 10875 */ 27685, 23740, 24285, 31691, 26733, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10890 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10905 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10920 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10935 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10950 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10965 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10980 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 10995 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36397, 19552,
  /* 11010 */ 18991, 25887, 28117, 32618, 26776, 29483, 29939, 26802, 24035, 24035, 24036, 28664, 23114, 23114, 23114,
  /* 11025 */ 22420, 30297, 23511, 23511, 23511, 29116, 19803, 24035, 24035, 24035, 25559, 26576, 23114, 23114, 23114,
  /* 11040 */ 30525, 33811, 22468, 23511, 23511, 23511, 28725, 27443, 22493, 24035, 24035, 27249, 24035, 24035, 23113,
  /* 11055 */ 23114, 23114, 26827, 23114, 28618, 29700, 23511, 23511, 26845, 23511, 34564, 20402, 24035, 24035, 26979,
  /* 11070 */ 24036, 23114, 23114, 23114, 24974, 23029, 22839, 23511, 23511, 23511, 26865, 25645, 24035, 24035, 24035,
  /* 11085 */ 26576, 23114, 23114, 23114, 32683, 22516, 23511, 23511, 23511, 23634, 24035, 24035, 23110, 23114, 23114,
  /* 11100 */ 20499, 23511, 23261, 23628, 33305, 24035, 25598, 23114, 19874, 34253, 27689, 19830, 24035, 23112, 19872,
  /* 11115 */ 27741, 23266, 24036, 23114, 26886, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007, 20046, 20132,
  /* 11130 */ 26578, 27685, 26931, 24569, 26439, 26947, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11145 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11160 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11175 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11190 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11205 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11220 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11235 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11250 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36019,
  /* 11265 */ 19288, 26995, 24035, 23112, 32618, 23511, 31507, 29939, 24035, 24035, 24035, 24036, 23114, 23114, 23114,
  /* 11280 */ 23114, 22420, 23511, 23511, 23511, 23511, 28306, 27043, 24035, 24035, 24035, 24035, 26576, 23114, 23114,
  /* 11295 */ 23114, 23114, 33811, 27061, 23511, 23511, 23511, 23511, 23512, 24694, 24035, 24035, 29978, 24035, 24035,
  /* 11310 */ 23113, 23114, 33114, 23114, 23114, 30010, 29700, 23511, 35913, 23511, 23511, 34585, 20402, 24035, 24035,
  /* 11325 */ 24035, 24036, 23114, 23114, 23114, 23114, 23029, 20271, 23511, 23511, 23511, 23511, 30562, 24035, 24035,
  /* 11340 */ 27155, 26576, 23114, 23114, 30447, 23036, 29695, 23511, 23511, 30935, 20099, 24152, 25529, 27100, 34461,
  /* 11355 */ 27121, 22625, 29156, 26009, 27137, 30422, 31903, 31655, 28870, 27171, 32439, 31731, 19830, 27232, 22612,
  /* 11370 */ 27265, 26786, 25494, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007, 20046,
  /* 11385 */ 20132, 26578, 27685, 20141, 20342, 27288, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11400 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11415 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11430 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11445 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11460 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11475 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11490 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11505 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11520 */ 36079, 19288, 21605, 27322, 27339, 28020, 27361, 27382, 29939, 24035, 24035, 32581, 24036, 23114, 23114,
  /* 11535 */ 23114, 27425, 22420, 23511, 23511, 23511, 27442, 28306, 19803, 24035, 24035, 24035, 24035, 26710, 23114,
  /* 11550 */ 23114, 23114, 23114, 32261, 22468, 23511, 23511, 23511, 23511, 35719, 24694, 29510, 24035, 24035, 24035,
  /* 11565 */ 24035, 26717, 23114, 23114, 23114, 23114, 28618, 32217, 23511, 23511, 23511, 23511, 34585, 20402, 24035,
  /* 11580 */ 24035, 24035, 27459, 23114, 23114, 23114, 36252, 23029, 20271, 23511, 23511, 23511, 28840, 30562, 24035,
  /* 11595 */ 24035, 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511, 23634, 24035, 24035, 23110,
  /* 11610 */ 23114, 23114, 23467, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035,
  /* 11625 */ 27480, 34483, 28401, 29761, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007,
  /* 11640 */ 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058,
  /* 11655 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11670 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11685 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11700 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11715 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11730 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11745 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11760 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11775 */ 19058, 36382, 19288, 21605, 27497, 27517, 28504, 28898, 27569, 29939, 29401, 27600, 27323, 27633, 19025,
  /* 11790 */ 27662, 23114, 27705, 22420, 20483, 27721, 23511, 27765, 28306, 19803, 23540, 24035, 24610, 27781, 27805,
  /* 11805 */ 26650, 23114, 28573, 32990, 25920, 22468, 26870, 23511, 26684, 34262, 34737, 25057, 34622, 24035, 24035,
  /* 11820 */ 23971, 24206, 27825, 27847, 23114, 23114, 27865, 27885, 35766, 27914, 23511, 23511, 32766, 32844, 27934,
  /* 11835 */ 28795, 26909, 27955, 26092, 27988, 25445, 28005, 28036, 28052, 21965, 23511, 32196, 19897, 28072, 28102,
  /* 11850 */ 36534, 21541, 23801, 28153, 28180, 28197, 28221, 23036, 32695, 28251, 28268, 28292, 23667, 34825, 23930,
  /* 11865 */ 24580, 28322, 28344, 31627, 28366, 25996, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 35625,
  /* 11880 */ 33477, 33359, 27674, 28393, 33992, 24036, 23114, 30243, 19829, 28417, 28433, 28463, 23008, 19876, 20208,
  /* 11895 */ 23007, 20046, 20132, 28489, 28520, 20141, 24569, 31691, 19787, 28550, 20268, 19058, 19058, 19058, 19058,
  /* 11910 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11925 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11940 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11955 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11970 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 11985 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12000 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12015 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12030 */ 19058, 19058, 36079, 19288, 21605, 24035, 23112, 32618, 23511, 31507, 29939, 24035, 24035, 24035, 24036,
  /* 12045 */ 23114, 23114, 23114, 23114, 22420, 23511, 23511, 23511, 23511, 28306, 19803, 24035, 24035, 24035, 24035,
  /* 12060 */ 26576, 23114, 23114, 23114, 23114, 33811, 22468, 23511, 23511, 23511, 23511, 23512, 24694, 28589, 24035,
  /* 12075 */ 24035, 24035, 24035, 28608, 23114, 23114, 23114, 23114, 28618, 20431, 23511, 23511, 23511, 23511, 34585,
  /* 12090 */ 20402, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 23029, 20271, 23511, 23511, 23511, 23511,
  /* 12105 */ 30562, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511, 23634, 24035,
  /* 12120 */ 24035, 23110, 23114, 23114, 23467, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689,
  /* 12135 */ 19830, 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876,
  /* 12150 */ 20208, 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058,
  /* 12165 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12180 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12195 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12210 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12225 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12240 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12255 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12270 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12285 */ 19058, 19058, 19058, 36004, 19288, 28634, 31951, 28565, 28702, 28718, 28741, 32544, 20175, 28792, 32086,
  /* 12300 */ 20105, 28811, 29059, 29862, 28856, 22420, 28886, 30354, 23359, 28922, 28306, 28952, 23888, 26320, 36506,
  /* 12315 */ 24035, 29331, 28968, 36609, 23114, 29003, 31661, 27061, 30649, 27366, 23511, 29023, 27918, 24694, 24035,
  /* 12330 */ 24035, 23893, 33094, 30867, 23113, 23114, 23114, 29044, 34184, 30010, 29700, 23511, 23511, 29081, 29102,
  /* 12345 */ 34585, 20402, 27789, 24035, 24035, 24036, 23114, 29132, 23114, 23114, 23029, 20271, 23511, 29153, 23511,
  /* 12360 */ 23511, 30562, 30174, 24035, 24035, 27409, 25438, 23114, 23114, 29172, 36668, 31332, 23511, 23511, 29192,
  /* 12375 */ 30144, 24035, 23110, 30203, 23114, 23467, 31544, 23261, 23628, 24035, 22545, 23111, 23114, 29213, 27078,
  /* 12390 */ 27689, 29234, 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 29257, 23008,
  /* 12405 */ 19876, 20208, 28768, 29290, 29320, 34776, 29353, 20141, 22435, 29378, 19787, 29304, 20268, 19058, 19058,
  /* 12420 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12435 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12450 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12465 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12480 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12495 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12510 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12525 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12540 */ 19058, 19058, 19058, 19058, 36367, 19288, 21605, 34616, 19006, 32618, 31497, 31507, 36216, 20184, 24035,
  /* 12555 */ 34393, 29424, 34668, 23114, 34900, 29447, 22420, 30360, 23511, 37089, 29473, 28306, 19803, 29499, 24398,
  /* 12570 */ 24035, 24035, 26576, 31799, 29532, 29550, 23114, 33811, 22468, 32298, 29571, 31184, 23511, 23512, 37127,
  /* 12585 */ 36628, 29589, 24035, 24135, 24035, 23113, 29608, 23114, 27831, 29634, 28618, 29652, 30037, 23511, 24172,
  /* 12600 */ 29671, 34585, 20402, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 29555, 29690, 23511, 23511,
  /* 12615 */ 23511, 23511, 30562, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511,
  /* 12630 */ 23634, 29719, 24035, 23110, 29738, 23114, 23467, 34035, 29756, 23628, 24035, 24035, 23111, 23114, 19874,
  /* 12645 */ 27078, 27689, 19830, 24035, 23112, 19872, 27741, 29777, 34364, 28181, 30243, 29799, 31920, 27272, 27185,
  /* 12660 */ 23008, 31126, 20208, 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29828, 20268, 19058,
  /* 12675 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12690 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12705 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12720 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12735 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12750 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12765 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12780 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12795 */ 19058, 19058, 19058, 19058, 19058, 35989, 19552, 19687, 35139, 28649, 29878, 29894, 29924, 29939, 23224,
  /* 12810 */ 23085, 31969, 24036, 35173, 24752, 24803, 23114, 22420, 31190, 30318, 24870, 23511, 28306, 29967, 23967,
  /* 12825 */ 24035, 24035, 24035, 26576, 30000, 23114, 23114, 23114, 33811, 22468, 30026, 23511, 23511, 23511, 23512,
  /* 12840 */ 26078, 24035, 24035, 24035, 30053, 37137, 30071, 23114, 23114, 33368, 25136, 28618, 30723, 23511, 23511,
  /* 12855 */ 37096, 31356, 34585, 20402, 30092, 30127, 30160, 24036, 35740, 30219, 24960, 30259, 23029, 20271, 34042,
  /* 12870 */ 30285, 30342, 30376, 23289, 30055, 30400, 30419, 30438, 32640, 33532, 33514, 30472, 18792, 26267, 24323,
  /* 12885 */ 23057, 30493, 23639, 20008, 30196, 33188, 30517, 20075, 23511, 30541, 23628, 30578, 33928, 28776, 30594,
  /* 12900 */ 19874, 30610, 30637, 19830, 30677, 27646, 19872, 25779, 23266, 23232, 35016, 30243, 30696, 29812, 30712,
  /* 12915 */ 30746, 27206, 30779, 30807, 23007, 33395, 20132, 26578, 27685, 31703, 22928, 31691, 19787, 31079, 20268,
  /* 12930 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12945 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12960 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12975 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 12990 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13005 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13020 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13035 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13050 */ 19058, 19058, 19058, 19058, 19058, 19058, 36352, 19288, 23335, 30841, 26131, 30888, 30904, 30986, 29939,
  /* 13065 */ 24035, 24704, 31017, 20025, 23114, 26178, 31051, 31095, 22420, 23511, 22524, 31142, 31172, 28534, 31206,
  /* 13080 */ 35497, 25196, 24035, 28592, 24503, 23114, 31239, 31285, 23114, 31305, 31321, 31355, 31372, 31407, 23511,
  /* 13095 */ 30556, 24694, 24035, 27501, 19805, 24035, 24035, 23113, 23114, 31428, 24066, 23114, 28618, 29700, 23511,
  /* 13110 */ 31837, 18809, 23511, 34585, 31448, 24035, 24035, 24035, 23090, 23114, 23114, 23114, 23114, 31619, 35038,
  /* 13125 */ 23511, 23511, 23511, 23511, 33714, 24035, 33085, 24035, 29431, 23114, 31467, 23114, 23143, 31487, 23511,
  /* 13140 */ 31523, 23511, 35195, 36783, 24035, 30111, 23567, 23114, 23467, 31543, 31560, 23628, 24035, 24035, 23111,
  /* 13155 */ 23114, 19874, 30953, 31584, 34508, 24035, 31608, 26345, 37055, 23266, 31643, 31677, 31719, 31747, 31786,
  /* 13170 */ 31822, 26898, 23008, 19876, 31859, 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 31878, 31936,
  /* 13185 */ 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13200 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13215 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13230 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13245 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13260 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13275 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13290 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13305 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 35974, 19288, 21605, 27972, 35663, 31985, 29655, 32001,
  /* 13320 */ 36715, 24785, 25893, 23545, 31912, 19853, 19916, 25938, 24540, 22420, 31843, 29674, 29573, 32735, 28936,
  /* 13335 */ 19803, 24035, 24035, 32047, 24035, 26576, 23114, 23114, 27544, 23114, 33811, 22468, 23511, 23511, 32161,
  /* 13350 */ 23511, 23512, 32066, 24035, 33313, 24035, 24035, 24035, 23113, 27426, 32102, 23114, 23114, 28618, 32125,
  /* 13365 */ 23511, 32144, 23511, 23511, 33569, 20402, 24035, 27045, 24035, 24036, 23114, 23114, 28328, 23114, 30076,
  /* 13380 */ 32177, 23511, 23511, 30384, 23511, 30562, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23595, 32212,
  /* 13395 */ 23511, 23511, 23511, 23634, 24035, 24035, 23110, 23114, 23114, 23467, 23511, 23261, 23628, 24035, 24035,
  /* 13410 */ 23111, 23114, 19874, 27078, 27689, 19830, 24035, 23112, 19872, 22635, 25753, 32233, 32257, 32277, 19829,
  /* 13425 */ 26577, 26597, 20211, 23008, 19876, 32322, 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787,
  /* 13440 */ 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13455 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13470 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13485 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13500 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13515 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13530 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13545 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13560 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36079, 19288, 32352, 35285, 32380, 34196, 33016,
  /* 13575 */ 30661, 29939, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 22420, 23511, 23511, 23511, 23511,
  /* 13590 */ 28306, 32404, 24035, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23114, 33811, 32422, 23511, 23511,
  /* 13605 */ 23511, 23511, 23512, 24694, 24035, 24035, 24035, 24035, 24035, 23113, 23114, 23114, 23114, 23114, 30269,
  /* 13620 */ 29700, 23511, 23511, 23511, 23511, 34585, 20402, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114,
  /* 13635 */ 23029, 20271, 23511, 23511, 23511, 23511, 30562, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23036,
  /* 13650 */ 29695, 23511, 23511, 23511, 23634, 24035, 24035, 23110, 23114, 23114, 23467, 23511, 23261, 23628, 19949,
  /* 13665 */ 24035, 23111, 32455, 19874, 31269, 27689, 19830, 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243,
  /* 13680 */ 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691,
  /* 13695 */ 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13710 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13725 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13740 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13755 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13770 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13785 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13800 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13815 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36337, 19552, 19209, 21617, 26509, 32475,
  /* 13830 */ 32491, 32529, 29939, 24035, 32578, 25241, 32597, 23114, 32634, 29007, 32656, 22420, 23511, 32729, 26365,
  /* 13845 */ 32751, 28306, 32788, 32882, 24035, 24035, 32813, 36727, 23114, 33182, 23114, 27553, 33235, 32829, 23511,
  /* 13860 */ 32706, 23511, 28906, 28377, 26962, 32881, 32904, 32898, 32920, 24035, 32953, 23114, 32977, 26408, 23114,
  /* 13875 */ 28164, 33006, 23511, 33039, 35774, 23511, 32306, 20402, 33076, 30872, 24035, 24036, 25408, 33110, 28979,
  /* 13890 */ 23114, 23029, 20271, 35835, 33130, 33054, 23511, 30562, 33148, 24035, 24035, 33167, 23114, 23114, 33775,
  /* 13905 */ 23036, 20459, 23511, 23511, 25464, 24646, 24035, 24035, 22446, 23114, 23114, 25627, 23511, 23261, 23628,
  /* 13920 */ 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035, 23112, 19872, 27741, 31391, 33204, 33220,
  /* 13935 */ 33251, 33287, 26577, 26597, 20211, 33329, 19876, 33345, 23007, 20046, 20132, 26578, 27685, 28473, 22599,
  /* 13950 */ 31691, 33411, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13965 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13980 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 13995 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14010 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14025 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14040 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14055 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14070 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 35959, 19288, 21907, 27243, 29843,
  /* 14085 */ 32618, 33427, 31507, 29939, 33460, 34090, 24035, 24036, 33493, 24416, 33530, 23114, 22420, 33548, 24379,
  /* 14100 */ 33585, 23511, 28306, 19803, 33603, 24202, 24035, 24035, 25593, 33749, 28205, 23114, 23114, 32388, 22468,
  /* 14115 */ 33853, 33060, 23511, 23511, 31339, 33621, 24035, 24035, 34397, 24618, 30757, 33663, 23114, 23114, 33683,
  /* 14130 */ 35684, 28618, 26678, 23511, 23511, 32506, 33699, 34585, 20402, 24035, 32562, 26973, 24036, 23114, 23114,
  /* 14145 */ 33377, 33773, 23029, 20271, 23511, 23511, 30621, 23511, 23860, 24035, 33791, 21553, 26576, 36558, 23114,
  /* 14160 */ 33809, 23036, 32857, 26047, 23511, 33827, 23634, 24035, 24035, 23110, 23114, 23114, 31252, 23511, 33845,
  /* 14175 */ 23628, 24035, 24459, 23111, 23114, 33869, 27078, 30791, 29783, 24035, 24742, 19872, 33895, 23266, 26462,
  /* 14190 */ 19710, 33879, 33919, 26577, 26597, 24123, 24930, 21930, 20208, 30501, 33953, 25268, 20252, 33983, 20141,
  /* 14205 */ 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14220 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14235 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14250 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14265 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14280 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14295 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14310 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14325 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36322, 19552, 23390, 33634,
  /* 14340 */ 35154, 34008, 34024, 34058, 35544, 34106, 34128, 26811, 33151, 34144, 34169, 34212, 23114, 34228, 34244,
  /* 14355 */ 34278, 34315, 23511, 34331, 34347, 34380, 34413, 24035, 24663, 26576, 34429, 34453, 34477, 29534, 33811,
  /* 14370 */ 22468, 34499, 34524, 34557, 25170, 34580, 35436, 23937, 34601, 24035, 24341, 26453, 23113, 34638, 34662,
  /* 14385 */ 23114, 24236, 28618, 34684, 34703, 34729, 23511, 35352, 34753, 34799, 24035, 34815, 32558, 34848, 34888,
  /* 14400 */ 35814, 34923, 23165, 29137, 23606, 30326, 30730, 34939, 33023, 30562, 36848, 34979, 24035, 24847, 34996,
  /* 14415 */ 23114, 23114, 35032, 29695, 35054, 23511, 23511, 35091, 33296, 35124, 24296, 28235, 24361, 36276, 32772,
  /* 14430 */ 35067, 35189, 27301, 30855, 24852, 22452, 35211, 35237, 35316, 25500, 35270, 23405, 24304, 35304, 29362,
  /* 14445 */ 24036, 23114, 35332, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 35368, 28823, 23920, 32336, 35405,
  /* 14460 */ 20141, 24569, 31691, 35421, 35479, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14475 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14490 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14505 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14520 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14535 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14550 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14565 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14580 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 35944, 22795, 21605,
  /* 14595 */ 33647, 35877, 35513, 30962, 35529, 34073, 35557, 24035, 24035, 20405, 31107, 23114, 23114, 23114, 35590,
  /* 14610 */ 34713, 23511, 23511, 23511, 35641, 19803, 29408, 32937, 25298, 24035, 35657, 23115, 27849, 24760, 35679,
  /* 14625 */ 26205, 22468, 23511, 35700, 24907, 24901, 35075, 31893, 34980, 24035, 24035, 24035, 24035, 23113, 35009,
  /* 14640 */ 23114, 23114, 23114, 28618, 35716, 30970, 23511, 23511, 23511, 34585, 23215, 24035, 24035, 24035, 24036,
  /* 14655 */ 35735, 23114, 23114, 23114, 27105, 35756, 35790, 23511, 23511, 23511, 35254, 35446, 24035, 24035, 31223,
  /* 14670 */ 35809, 23114, 23114, 23036, 36825, 35830, 23511, 23511, 23634, 24035, 24035, 23110, 23114, 23114, 23467,
  /* 14685 */ 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 31031, 20355, 19872, 33903,
  /* 14700 */ 23266, 24036, 23114, 28686, 19829, 26577, 26597, 20211, 23008, 23424, 20208, 24711, 31065, 24486, 26578,
  /* 14715 */ 27685, 20141, 19773, 35851, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14730 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14745 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14760 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14775 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14790 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14805 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14820 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14835 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 36307, 19288,
  /* 14850 */ 21605, 35494, 19702, 32618, 33437, 31507, 29939, 25117, 24035, 27939, 24036, 27869, 23114, 26829, 23114,
  /* 14865 */ 22420, 23494, 23511, 33132, 23511, 28306, 19803, 24035, 34832, 24035, 24035, 26576, 23114, 25153, 23114,
  /* 14880 */ 23114, 33811, 22468, 23511, 23511, 35911, 23511, 23512, 24694, 24035, 24035, 24035, 24035, 24035, 23113,
  /* 14895 */ 23114, 23114, 23114, 23114, 28618, 29700, 23511, 23511, 23511, 23511, 34585, 20402, 24035, 24035, 24035,
  /* 14910 */ 24036, 23114, 23114, 23114, 23114, 23029, 20271, 23511, 23511, 23511, 23511, 30562, 24035, 24035, 24035,
  /* 14925 */ 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511, 23634, 24035, 24035, 23110, 23114, 23114,
  /* 14940 */ 23467, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035, 23112, 19872,
  /* 14955 */ 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007, 20046, 20132,
  /* 14970 */ 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 14985 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15000 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15015 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15030 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15045 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15060 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15075 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15090 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 35929,
  /* 15105 */ 19288, 21605, 25860, 23112, 36185, 23511, 36201, 29939, 24035, 24035, 24035, 24036, 23114, 23114, 23114,
  /* 15120 */ 23114, 22420, 23511, 23511, 23511, 23511, 28306, 19803, 24035, 24035, 24035, 24035, 26576, 23114, 23114,
  /* 15135 */ 23114, 23114, 33811, 22468, 23511, 23511, 23511, 23511, 23512, 26748, 24035, 24035, 24035, 24035, 24035,
  /* 15150 */ 36249, 23114, 23114, 23114, 23114, 28618, 28835, 23511, 23511, 23511, 23511, 34585, 20402, 24035, 27151,
  /* 15165 */ 24035, 26760, 23114, 27989, 23114, 23114, 36268, 20271, 23511, 24436, 23511, 29703, 30562, 24035, 24035,
  /* 15180 */ 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511, 23634, 24035, 24035, 23110, 23114,
  /* 15195 */ 23114, 23467, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035, 23112,
  /* 15210 */ 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007, 20046,
  /* 15225 */ 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15240 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15255 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15270 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15285 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15300 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15315 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15330 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15345 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15360 */ 36292, 19288, 21605, 36503, 21922, 32618, 34534, 31507, 36522, 24035, 33793, 24035, 35864, 23114, 23114,
  /* 15375 */ 36555, 23417, 22420, 23511, 23511, 36574, 26020, 28306, 19803, 24035, 24035, 24035, 24035, 26576, 23114,
  /* 15390 */ 23114, 23114, 23114, 33811, 22468, 23511, 23511, 23511, 23511, 23512, 36592, 24035, 24035, 36625, 24035,
  /* 15405 */ 24035, 23113, 23114, 32961, 23114, 23114, 29618, 29700, 23511, 29086, 23511, 23511, 34585, 20402, 36644,
  /* 15420 */ 24035, 24035, 24036, 29740, 23114, 23114, 23114, 29065, 36663, 31527, 23511, 23511, 23511, 30562, 24035,
  /* 15435 */ 24035, 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511, 23634, 24035, 24035, 23110,
  /* 15450 */ 23114, 23114, 23467, 23511, 23261, 23628, 24035, 24035, 23111, 23114, 19874, 27078, 27689, 19830, 24035,
  /* 15465 */ 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208, 23007,
  /* 15480 */ 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058, 19058,
  /* 15495 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15510 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15525 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15540 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15555 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15570 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15585 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15600 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15615 */ 19058, 36079, 19288, 21605, 31451, 23112, 36684, 23511, 36700, 29939, 24035, 24035, 24035, 30185, 23114,
  /* 15630 */ 23114, 23114, 27526, 22420, 23511, 23511, 23511, 32865, 28306, 19803, 36743, 24035, 27017, 24035, 26576,
  /* 15645 */ 27535, 23114, 31432, 23114, 33811, 22468, 33271, 23511, 32128, 23511, 23512, 24694, 24035, 27196, 24035,
  /* 15660 */ 24035, 24035, 23113, 32459, 23114, 23114, 23114, 28618, 29700, 33829, 36762, 23511, 23511, 34585, 20402,
  /* 15675 */ 24035, 36746, 24035, 29722, 23114, 23114, 34437, 23114, 34907, 20271, 23511, 23511, 18801, 23511, 23206,
  /* 15690 */ 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511, 23511, 23511, 36837, 24035, 24035,
  /* 15705 */ 33739, 23114, 23114, 25094, 23511, 23261, 23628, 24035, 36780, 23111, 24073, 19874, 27078, 35344, 19830,
  /* 15720 */ 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577, 26597, 20211, 23008, 19876, 20208,
  /* 15735 */ 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304, 20268, 19058, 19058, 19058, 19058,
  /* 15750 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15765 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15780 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15795 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15810 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15825 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15840 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15855 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 15870 */ 19058, 19058, 22720, 19288, 36799, 36866, 17466, 36890, 36864, 21991, 22211, 22987, 17556, 17575, 22288,
  /* 15885 */ 17486, 17509, 17525, 18373, 17631, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411, 20306, 17996,
  /* 15900 */ 17689, 17470, 17591, 20896, 17468, 36883, 36906, 36867, 19404, 20299, 36866, 17647, 17862, 18921, 19514,
  /* 15915 */ 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008, 37024,
  /* 15930 */ 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906, 17928,
  /* 15945 */ 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935, 18262, 18278,
  /* 15960 */ 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583, 19149, 18638,
  /* 15975 */ 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054, 17838,
  /* 15990 */ 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058, 19058, 19058,
  /* 16005 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16020 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16035 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16050 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16065 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16080 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16095 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16110 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16125 */ 19058, 19058, 19058, 22705, 19288, 19457, 36866, 17466, 36890, 36866, 19375, 22971, 22987, 17556, 17575,
  /* 16140 */ 22288, 17486, 17509, 17525, 18373, 18855, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411, 20306,
  /* 16155 */ 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647, 17862, 18921,
  /* 16170 */ 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712, 37008,
  /* 16185 */ 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890, 17906,
  /* 16200 */ 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935, 18262,
  /* 16215 */ 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583, 19149,
  /* 16230 */ 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915, 22054,
  /* 16245 */ 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058, 19058,
  /* 16260 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16275 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16290 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16305 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16320 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16335 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16350 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16365 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16380 */ 19058, 19058, 19058, 19058, 36124, 19288, 36951, 36866, 17466, 36890, 36866, 21991, 22404, 22987, 17556,
  /* 16395 */ 17575, 22288, 17486, 17509, 17525, 18373, 18567, 22984, 17553, 17572, 22285, 18462, 17990, 18622, 19411,
  /* 16410 */ 20306, 17996, 17689, 17470, 17591, 20896, 17468, 36979, 36995, 36867, 19404, 20299, 36866, 17647, 17862,
  /* 16425 */ 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521, 17712,
  /* 16440 */ 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884, 18890,
  /* 16455 */ 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134, 36935,
  /* 16470 */ 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553, 18583,
  /* 16485 */ 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906, 20915,
  /* 16500 */ 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056, 19058,
  /* 16515 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16530 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16545 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16560 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16575 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16590 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16605 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16620 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16635 */ 19058, 19058, 19058, 19058, 19058, 36139, 19288, 19457, 36866, 17466, 36890, 36866, 21991, 22971, 22987,
  /* 16650 */ 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18027, 22984, 17553, 17572, 22285, 18462, 17990, 18622,
  /* 16665 */ 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 17619, 22083, 36867, 19404, 20299, 36866, 17647,
  /* 16680 */ 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403, 18928, 19521,
  /* 16695 */ 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064, 18218, 17884,
  /* 16710 */ 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010, 25026, 18134,
  /* 16725 */ 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485, 18523, 18553,
  /* 16740 */ 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681, 22026, 20906,
  /* 16755 */ 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976, 19041, 19056,
  /* 16770 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16785 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16800 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16815 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16830 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16845 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16860 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16875 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 16890 */ 19058, 19058, 19058, 19058, 19058, 19058, 36139, 19288, 21529, 24035, 23112, 23033, 23511, 31507, 25377,
  /* 16905 */ 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 37040, 23511, 23511, 23511, 23511, 28086, 19803,
  /* 16920 */ 24035, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23114, 24254, 37079, 23511, 23511, 23511, 23511,
  /* 16935 */ 23512, 34766, 24035, 24035, 24035, 24035, 24035, 23113, 23114, 23114, 23114, 23114, 28618, 29700, 23511,
  /* 16950 */ 23511, 23511, 23511, 34585, 20402, 24035, 24035, 24035, 24036, 23114, 23114, 23114, 23114, 23029, 20271,
  /* 16965 */ 23511, 23511, 23511, 23511, 30562, 24035, 24035, 24035, 26576, 23114, 23114, 23114, 23036, 29695, 23511,
  /* 16980 */ 23511, 23511, 23634, 24035, 24035, 23110, 23114, 23114, 23467, 23511, 23261, 23628, 24035, 24035, 23111,
  /* 16995 */ 23114, 19874, 27078, 27689, 19830, 24035, 23112, 19872, 27741, 23266, 24036, 23114, 30243, 19829, 26577,
  /* 17010 */ 26597, 20211, 23008, 19876, 20208, 23007, 20046, 20132, 26578, 27685, 20141, 24569, 31691, 19787, 29304,
  /* 17025 */ 20268, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17040 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17055 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17070 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17085 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17100 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17115 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17130 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17145 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 37112, 37160, 18469, 36866, 17466, 36890, 36866, 17656,
  /* 17160 */ 37174, 22987, 17556, 17575, 22288, 17486, 17509, 17525, 18373, 18537, 22984, 17553, 17572, 22285, 18780,
  /* 17175 */ 17990, 18622, 19411, 20306, 17996, 17689, 17470, 17591, 20896, 17468, 36883, 36906, 36867, 19404, 20299,
  /* 17190 */ 36866, 17647, 17862, 18921, 19514, 17705, 20311, 37017, 17728, 17756, 17784, 17800, 17825, 17854, 18403,
  /* 17205 */ 18928, 19521, 17712, 37008, 37024, 17878, 18884, 17900, 17922, 17944, 18178, 17960, 18012, 18381, 18064,
  /* 17220 */ 18218, 17884, 18890, 17906, 17928, 18102, 25022, 18130, 36931, 36963, 17493, 18150, 18166, 18214, 25010,
  /* 17235 */ 25026, 18134, 36935, 18262, 18278, 18294, 18320, 18336, 18361, 18397, 18274, 22096, 18304, 18448, 18485,
  /* 17250 */ 18523, 18553, 18583, 19149, 18638, 18497, 19656, 18664, 18680, 18507, 18696, 19164, 18712, 18737, 17681,
  /* 17265 */ 22026, 20906, 20915, 22054, 17838, 17450, 22022, 18765, 19225, 18841, 18871, 18906, 19241, 19257, 18976,
  /* 17280 */ 19041, 19056, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17295 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17310 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17325 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17340 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17355 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17370 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17385 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058,
  /* 17400 */ 19058, 19058, 19058, 19058, 19058, 19058, 19058, 19058, 53264, 18, 49172, 57366, 24, 8192, 28, 102432,
  /* 17416 */ 127011, 110630, 114730, 106539, 127011, 127011, 127011, 53264, 18, 18, 0, 0, 57366, 0, 24, 24, 24, 0, 28,
  /* 17435 */ 28, 28, 28, 102432, 0, 0, 127011, 0, 2220032, 110630, 0, 0, 0, 114730, 106539, 0, 2170880, 2170880,
  /* 17453 */ 2170880, 2170880, 0, 0, 0, 2170880, 2170880, 2170880, 3002368, 2170880, 2170880, 2170880, 2170880,
  /* 17466 */ 2170880, 2170880, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 17477 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2576384, 2215936, 2215936, 2215936,
  /* 17488 */ 2416640, 2424832, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 17499 */ 2215936, 2215936, 2215936, 2543616, 2215936, 2215936, 2215936, 2215936, 2215936, 2629632, 2215936,
  /* 17510 */ 2617344, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2691072, 2215936, 2707456, 2215936,
  /* 17521 */ 2715648, 2215936, 2723840, 2764800, 2215936, 2215936, 2797568, 2215936, 2822144, 2215936, 2215936,
  /* 17532 */ 2854912, 2215936, 2215936, 2215936, 2912256, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 17543 */ 2215936, 0, 0, 0, 180224, 0, 0, 2174976, 0, 0, 2170880, 2617344, 2170880, 2170880, 2170880, 2170880,
  /* 17559 */ 2170880, 2170880, 2691072, 2170880, 2707456, 2170880, 2715648, 2170880, 2723840, 2764800, 2170880,
  /* 17570 */ 2170880, 2797568, 2170880, 2170880, 2797568, 2170880, 2822144, 2170880, 2170880, 2854912, 2170880,
  /* 17581 */ 2170880, 2170880, 2912256, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2215936,
  /* 17592 */ 2215936, 2215936, 2215936, 2609152, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2654208,
  /* 17603 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 0, 0, 0, 184599, 280, 0, 2174976, 0, 0,
  /* 17619 */ 2215936, 3117056, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 17630 */ 2215936, 2215936, 2215936, 0, 544, 0, 546, 0, 0, 2179072, 0, 0, 0, 552, 0, 0, 2170880, 2170880, 2170880,
  /* 17649 */ 3117056, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 17660 */ 2170880, 2170880, 0, 0, 0, 2158592, 2158592, 2232320, 2232320, 0, 2240512, 2240512, 0, 0, 0, 644, 0, 0, 0,
  /* 17679 */ 0, 0, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 3129344, 2170880, 2170880, 2170880,
  /* 17692 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2215936, 2215936, 2215936, 2400256, 2215936, 2215936,
  /* 17703 */ 2215936, 2215936, 2711552, 2170880, 2170880, 2170880, 2170880, 2170880, 2760704, 2768896, 2789376,
  /* 17714 */ 2813952, 2170880, 2170880, 2170880, 2875392, 2904064, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 17725 */ 2170880, 2170880, 2170880, 2170880, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 17736 */ 2215936, 2215936, 2453504, 2457600, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 0,
  /* 17748 */ 167936, 0, 0, 0, 0, 2174976, 0, 0, 2215936, 2215936, 2514944, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 17764 */ 2215936, 2215936, 2215936, 2592768, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 32768,
  /* 17776 */ 0, 0, 0, 0, 0, 2174976, 32768, 0, 2633728, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2711552,
  /* 17792 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2760704, 2768896, 2789376, 2813952, 2215936, 2215936,
  /* 17803 */ 2215936, 2875392, 2904064, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 17814 */ 2215936, 2215936, 0, 0, 0, 0, 0, 0, 2174976, 0, 65819, 2215936, 2215936, 3031040, 2215936, 3055616,
  /* 17830 */ 2215936, 2215936, 2215936, 2215936, 3092480, 2215936, 2215936, 3125248, 2215936, 2215936, 2215936,
  /* 17841 */ 2215936, 2215936, 2215936, 3002368, 2215936, 2215936, 2170880, 2170880, 2494464, 2170880, 2170880, 0, 0,
  /* 17854 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 3198976, 2215936, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 17872 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 0, 0, 0, 2379776, 2170880, 2170880, 2170880,
  /* 17885 */ 2170880, 2170880, 2170880, 2170880, 2445312, 2170880, 2465792, 2473984, 2170880, 2170880, 2170880,
  /* 17896 */ 2170880, 2170880, 2170880, 2523136, 2170880, 2170880, 2641920, 2170880, 2170880, 2170880, 2699264,
  /* 17907 */ 2170880, 2727936, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2879488, 2170880,
  /* 17918 */ 2916352, 2170880, 2170880, 2170880, 2879488, 2170880, 2916352, 2170880, 2170880, 2170880, 2170880,
  /* 17929 */ 2170880, 2170880, 2170880, 2170880, 2170880, 3026944, 2170880, 2170880, 3063808, 2170880, 2170880,
  /* 17940 */ 3112960, 2170880, 2170880, 3133440, 2170880, 2170880, 3112960, 2170880, 2170880, 3133440, 2170880,
  /* 17951 */ 2170880, 2170880, 3162112, 2170880, 2170880, 3182592, 3186688, 2170880, 2379776, 2215936, 2523136,
  /* 17962 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2596864, 2215936, 2621440, 2215936,
  /* 17973 */ 2215936, 2641920, 2215936, 2215936, 0, 0, 0, 0, 0, 0, 2179072, 548, 0, 0, 0, 0, 287, 2170880, 0, 2170880,
  /* 17993 */ 2170880, 2170880, 2400256, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 18004 */ 2170880, 2170880, 2170880, 3117056, 2170880, 2170880, 2170880, 2170880, 2215936, 2215936, 2699264,
  /* 18015 */ 2215936, 2727936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2879488, 2215936,
  /* 18026 */ 2916352, 2215936, 2215936, 0, 0, 0, 0, 188416, 0, 2179072, 0, 0, 0, 0, 0, 287, 2170880, 0, 2171019,
  /* 18045 */ 2171019, 2171019, 2400395, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 18056 */ 2171019, 2171019, 2171019, 3031179, 2171019, 3055755, 2171019, 2171019, 2215936, 3133440, 2215936,
  /* 18067 */ 2215936, 2215936, 3162112, 2215936, 2215936, 3182592, 3186688, 2215936, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 18085 */ 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2523275, 2171019, 2171019, 2171019, 2171019,
  /* 18096 */ 2171019, 2171019, 2171019, 2597003, 2171019, 2621579, 2170880, 2170880, 2170880, 3162112, 2170880,
  /* 18107 */ 2170880, 3182592, 3186688, 2170880, 0, 0, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 0,
  /* 18121 */ 53264, 0, 18, 18, 24, 24, 0, 4337664, 28, 2170880, 2170880, 2170880, 2629632, 2170880, 2170880, 2170880,
  /* 18137 */ 2170880, 2719744, 2744320, 2170880, 2170880, 2170880, 2834432, 2838528, 2170880, 2908160, 2170880,
  /* 18148 */ 2170880, 2936832, 2215936, 2215936, 2215936, 2215936, 2719744, 2744320, 2215936, 2215936, 2215936,
  /* 18159 */ 2834432, 2838528, 2215936, 2908160, 2215936, 2215936, 2936832, 2215936, 2215936, 2985984, 2215936,
  /* 18170 */ 2994176, 2215936, 2215936, 3014656, 2215936, 3059712, 3076096, 3088384, 2215936, 2215936, 2215936,
  /* 18181 */ 2215936, 2215936, 2215936, 2215936, 2445312, 2215936, 2465792, 2473984, 2215936, 2215936, 2215936,
  /* 18192 */ 2215936, 2215936, 2215936, 2171166, 2171166, 2171166, 2171166, 2171166, 0, 0, 0, 2171166, 2171166,
  /* 18205 */ 2171166, 2171166, 2171166, 2171166, 2171019, 2171019, 2494603, 2171019, 2171019, 2215936, 2215936,
  /* 18216 */ 2215936, 3215360, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2379776, 2170880, 2170880, 2170880, 2170880,
  /* 18236 */ 2985984, 2170880, 2994176, 2170880, 2170880, 3016168, 2170880, 3059712, 3076096, 3088384, 2170880,
  /* 18247 */ 2170880, 2170880, 2170880, 2170880, 2170880, 0, 53264, 0, 18, 18, 124, 124, 0, 128, 128, 2170880, 2170880,
  /* 18264 */ 2170880, 3215360, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2486272,
  /* 18276 */ 2170880, 2170880, 2506752, 2170880, 2170880, 2170880, 2535424, 2539520, 2170880, 2170880, 2588672,
  /* 18287 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2920448,
  /* 18298 */ 2170880, 2170880, 2170880, 2990080, 2170880, 2170880, 2170880, 2170880, 3051520, 2170880, 2170880,
  /* 18309 */ 2170880, 2170880, 2170880, 2170880, 3170304, 0, 2387968, 2392064, 2170880, 2170880, 2433024, 2170880,
  /* 18321 */ 2170880, 2170880, 3170304, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 18332 */ 2486272, 2215936, 2215936, 2506752, 2215936, 2215936, 2215936, 2535424, 2539520, 2215936, 2215936,
  /* 18343 */ 2588672, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 0, 0, 0, 0, 0, 0,
  /* 18358 */ 2174976, 136, 0, 2215936, 2215936, 2920448, 2215936, 2215936, 2215936, 2990080, 2215936, 2215936, 2215936,
  /* 18371 */ 2215936, 3051520, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 3108864, 2215936,
  /* 18382 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 3026944, 2215936, 2215936, 3063808,
  /* 18393 */ 2215936, 2215936, 3112960, 2215936, 2215936, 2215936, 3170304, 0, 0, 0, 0, 0, 0, 2170880, 2170880,
  /* 18408 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2453504, 2457600, 2170880, 2170880,
  /* 18419 */ 2170880, 2486272, 2170880, 2170880, 2506752, 2170880, 2170880, 2170880, 2537049, 2539520, 2170880,
  /* 18430 */ 2170880, 2588672, 2170880, 2170880, 2170880, 1508, 2170880, 2170880, 2170880, 1512, 2170880, 2920448,
  /* 18442 */ 2170880, 2170880, 2170880, 2990080, 2170880, 2170880, 2170880, 2461696, 2170880, 2170880, 2170880,
  /* 18453 */ 2510848, 2170880, 2170880, 2170880, 2170880, 2580480, 2170880, 2605056, 2637824, 2170880, 2170880, 18, 0,
  /* 18466 */ 0, 0, 0, 0, 0, 0, 0, 2220032, 0, 0, 0, 0, 0, 0, 0, 2170880, 2170880, 2170880, 2170880, 2686976, 2748416,
  /* 18487 */ 2170880, 2170880, 2170880, 2924544, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 18498 */ 3121152, 2170880, 2170880, 3145728, 3158016, 3166208, 2170880, 2420736, 2428928, 2170880, 2478080,
  /* 18509 */ 2170880, 2170880, 2170880, 2170880, 0, 0, 2170880, 2170880, 2170880, 2170880, 2646016, 2670592, 0, 0,
  /* 18523 */ 3145728, 3158016, 3166208, 2387968, 2392064, 2215936, 2215936, 2433024, 2215936, 2461696, 2215936,
  /* 18534 */ 2215936, 2215936, 2510848, 2215936, 2215936, 0, 0, 0, 0, 0, 0, 2179072, 0, 0, 0, 0, 0, 0, 2170880,
  /* 18553 */ 2215936, 2215936, 2580480, 2215936, 2605056, 2637824, 2215936, 2215936, 2686976, 2748416, 2215936,
  /* 18564 */ 2215936, 2215936, 2924544, 2215936, 2215936, 0, 0, 0, 0, 0, 0, 2179072, 0, 0, 0, 0, 0, 286, 2170880,
  /* 18583 */ 2215936, 2215936, 2215936, 2215936, 2215936, 3121152, 2215936, 2215936, 3145728, 3158016, 3166208,
  /* 18594 */ 2387968, 2392064, 2170880, 2170880, 2433024, 2170880, 2461696, 2170880, 2170880, 2170880, 2510848,
  /* 18605 */ 2170880, 2170880, 1625, 2170880, 2170880, 2580480, 2170880, 2605056, 2637824, 2170880, 647, 2170880,
  /* 18617 */ 2170880, 2170880, 2400256, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 18628 */ 2170880, 2170880, 2576384, 2170880, 2170880, 2170880, 2170880, 2170880, 2609152, 2170880, 2170880,
  /* 18639 */ 2686976, 0, 0, 2748416, 2170880, 2170880, 0, 2170880, 2924544, 2170880, 2170880, 2170880, 2170880,
  /* 18652 */ 2170880, 2170880, 0, 53264, 0, 18, 18, 24, 0, 0, 28, 28, 2170880, 3141632, 2215936, 2420736, 2428928,
  /* 18669 */ 2215936, 2478080, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2646016,
  /* 18680 */ 2670592, 2752512, 2756608, 2846720, 2961408, 2215936, 2998272, 2215936, 3010560, 2215936, 2215936,
  /* 18691 */ 2215936, 3141632, 2170880, 2420736, 2428928, 2752512, 2756608, 0, 2846720, 2961408, 2170880, 2998272,
  /* 18703 */ 2170880, 3010560, 2170880, 2170880, 2170880, 3141632, 2170880, 2170880, 2490368, 2215936, 2490368,
  /* 18714 */ 2215936, 2215936, 2215936, 2547712, 2555904, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 18725 */ 2215936, 2215936, 2215936, 0, 0, 0, 0, 0, 0, 2174976, 245760, 0, 3129344, 2170880, 2170880, 2490368,
  /* 18741 */ 2170880, 2170880, 2170880, 0, 0, 2547712, 2555904, 2170880, 2170880, 2170880, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 18760 */ 2220032, 0, 0, 45056, 0, 2584576, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2170880,
  /* 18774 */ 2170880, 2170880, 2170880, 0, 0, 0, 2170880, 2170880, 2158592, 0, 0, 0, 0, 0, 0, 0, 0, 2220032, 0, 0, 0,
  /* 18795 */ 0, 0, 0, 0, 0, 1482, 97, 97, 97, 97, 97, 97, 97, 1354, 97, 97, 97, 97, 97, 97, 97, 97, 1148, 97, 97, 97,
  /* 18821 */ 97, 97, 97, 97, 2584576, 2170880, 2170880, 1512, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 18836 */ 2441216, 2170880, 2527232, 2170880, 2600960, 2170880, 2850816, 2170880, 2170880, 2170880, 3022848,
  /* 18847 */ 2215936, 2441216, 2215936, 2527232, 2215936, 2600960, 2215936, 2850816, 2215936, 2215936, 0, 0, 0, 0, 0,
  /* 18862 */ 0, 2179072, 0, 0, 0, 0, 0, 287, 2170880, 2215936, 3022848, 2170880, 2441216, 2170880, 2527232, 0, 0,
  /* 18879 */ 2170880, 2600960, 2170880, 0, 2850816, 2170880, 2170880, 2170880, 2170880, 2170880, 2523136, 2170880,
  /* 18891 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2596864, 2170880, 2621440, 2170880, 2170880,
  /* 18902 */ 2641920, 2170880, 2170880, 2170880, 3022848, 2170880, 2519040, 2170880, 2170880, 2170880, 2170880,
  /* 18913 */ 2170880, 2215936, 2519040, 2215936, 2215936, 2215936, 2215936, 2215936, 2170880, 2170880, 2170880,
  /* 18924 */ 2453504, 2457600, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2514944, 2170880, 2170880,
  /* 18935 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2592768, 2170880, 2170880, 2519040, 0, 2024,
  /* 18947 */ 2170880, 2170880, 0, 2170880, 2170880, 2170880, 2396160, 2170880, 2170880, 2170880, 2170880, 3018752,
  /* 18959 */ 2396160, 2215936, 2215936, 2215936, 2215936, 3018752, 2396160, 0, 2024, 2170880, 2170880, 2170880,
  /* 18971 */ 2170880, 3018752, 2170880, 2650112, 2965504, 2170880, 2215936, 2650112, 2965504, 2215936, 0, 0, 2170880,
  /* 18984 */ 2650112, 2965504, 2170880, 2551808, 2170880, 2551808, 2215936, 0, 0, 0, 0, 37, 110630, 0, 0, 0, 114730,
  /* 19001 */ 106539, 41098, 45, 45, 141, 45, 45, 67, 67, 67, 67, 67, 224, 67, 67, 238, 67, 67, 67, 67, 67, 67, 67,
  /* 19024 */ 1288, 67, 67, 67, 67, 67, 67, 67, 67, 67, 469, 67, 67, 67, 67, 67, 67, 0, 2551808, 2170880, 2170880,
  /* 19045 */ 2215936, 0, 2170880, 2170880, 2215936, 0, 2170880, 2170880, 2215936, 0, 2170880, 2977792, 2977792, 0, 0,
  /* 19060 */ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 53264, 18, 49172, 57366, 24, 8192, 29, 102432, 127011, 110630,
  /* 19084 */ 114730, 106539, 127011, 127011, 127011, 53264, 18, 18, 49172, 0, 0, 0, 24, 24, 24, 0, 28, 28, 28, 28,
  /* 19104 */ 102432, 127, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 140, 2170880, 2170880, 2170880, 2416640, 0, 0, 0, 0, 2220032,
  /* 19126 */ 110630, 0, 0, 0, 114730, 106539, 136, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 0, 53264, 0,
  /* 19142 */ 4256099, 4256099, 24, 24, 0, 28, 28, 2170880, 2461696, 2170880, 2170880, 2170880, 2510848, 2170880,
  /* 19156 */ 2170880, 0, 2170880, 2170880, 2580480, 2170880, 2605056, 2637824, 2170880, 2170880, 2170880, 2547712,
  /* 19168 */ 2555904, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 3129344,
  /* 19179 */ 2215936, 2215936, 543, 543, 545, 545, 0, 0, 2179072, 0, 550, 551, 551, 0, 287, 2171166, 2171166, 18, 0, 0,
  /* 19199 */ 0, 0, 0, 0, 0, 0, 2220032, 0, 0, 645, 0, 0, 0, 0, 37, 110630, 0, 0, 0, 114730, 106539, 41098, 45, 45, 45,
  /* 19224 */ 149, 2584576, 2170880, 2170880, 0, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2441216,
  /* 19237 */ 2170880, 2527232, 2170880, 2600960, 2519040, 0, 0, 2170880, 2170880, 0, 2170880, 2170880, 2170880,
  /* 19250 */ 2396160, 2170880, 2170880, 2170880, 2170880, 3018752, 2396160, 2215936, 2215936, 2215936, 2215936,
  /* 19261 */ 3018752, 2396160, 0, 0, 2170880, 2170880, 2170880, 2170880, 3018752, 2170880, 2650112, 2965504, 53264, 18,
  /* 19275 */ 49172, 57366, 24, 155648, 28, 102432, 155648, 155687, 114730, 106539, 0, 0, 155648, 53264, 18, 18, 49172,
  /* 19292 */ 0, 57366, 0, 24, 24, 24, 0, 28, 28, 28, 28, 102432, 0, 0, 0, 0, 2220032, 0, 94208, 0, 0, 114730, 106539,
  /* 19315 */ 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 0, 53264, 208896, 18, 278528, 24, 24, 0, 28, 28,
  /* 19332 */ 53264, 18, 159765, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 0, 53264, 18, 18, 49172,
  /* 19351 */ 0, 57366, 0, 24, 24, 24, 0, 28, 139394, 28, 28, 102432, 131, 0, 0, 0, 2220032, 110630, 0, 0, 0, 114730,
  /* 19373 */ 106539, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 32768, 53264, 0, 18, 18, 24, 24, 0, 28,
  /* 19390 */ 28, 0, 546, 0, 0, 2183168, 0, 0, 552, 832, 2170880, 2170880, 2170880, 2400256, 2170880, 2170880, 2170880,
  /* 19407 */ 2170880, 2170880, 2609152, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2654208, 2170880,
  /* 19418 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2215936, 2215936,
  /* 19429 */ 2215936, 2215936, 2215936, 2215936, 3198976, 2215936, 0, 1084, 0, 1088, 0, 1092, 0, 0, 0, 0, 0, 41606, 0,
  /* 19448 */ 0, 0, 0, 45, 45, 45, 45, 45, 937, 0, 0, 0, 0, 2220032, 110630, 0, 0, 0, 114730, 106539, 0, 2170880,
  /* 19470 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 3198976, 2170880, 0, 0, 644, 0, 0, 0,
  /* 19485 */ 2215936, 3117056, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 19496 */ 2215936, 2215936, 2215936, 0, 826, 0, 828, 0, 0, 2183168, 0, 0, 830, 0, 2170880, 2170880, 2170880,
  /* 19513 */ 2400256, 2170880, 2170880, 2170880, 2170880, 2592768, 2170880, 2170880, 2170880, 2170880, 2633728,
  /* 19524 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2711552, 2170880, 2170880, 2170880, 2170880,
  /* 19535 */ 2170880, 2760704, 53264, 18, 49172, 57366, 24, 8192, 28, 172066, 172032, 110630, 172066, 106539, 0, 0,
  /* 19551 */ 172032, 53264, 18, 18, 49172, 0, 57366, 0, 24, 24, 24, 16384, 28, 28, 28, 28, 102432, 0, 98304, 0, 0,
  /* 19572 */ 2220032, 110630, 0, 0, 0, 0, 106539, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 19587 */ 2170880, 3198976, 2170880, 0, 0, 45056, 0, 0, 0, 53264, 18, 49172, 57366, 25, 8192, 30, 102432, 0, 110630,
  /* 19606 */ 114730, 106539, 0, 0, 176219, 53264, 18, 18, 49172, 0, 57366, 0, 124, 124, 124, 0, 128, 128, 128, 128,
  /* 19626 */ 102432, 128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 140, 2170880, 2170880, 2170880, 2416640, 0, 546, 0, 0, 2183168,
  /* 19648 */ 0, 65536, 552, 0, 2170880, 2170880, 2170880, 2400256, 2170880, 2170880, 2170880, 2170880, 2646016,
  /* 19661 */ 2670592, 2752512, 2756608, 2846720, 2961408, 2170880, 2998272, 2170880, 3010560, 2170880, 2170880,
  /* 19672 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 3198976, 2215936, 0, 0, 0, 0, 0, 0, 65536, 0, 0, 0,
  /* 19690 */ 0, 37, 110630, 0, 0, 0, 114730, 106539, 41098, 45, 45, 143, 45, 45, 67, 67, 67, 67, 67, 227, 67, 67, 67,
  /* 19713 */ 67, 67, 67, 67, 67, 67, 1824, 67, 1826, 67, 67, 67, 67, 17, 18, 49172, 57366, 24, 8192, 28, 102432, 0,
  /* 19735 */ 110630, 114730, 106539, 0, 0, 32768, 120, 121, 18, 18, 49172, 0, 57366, 0, 24, 24, 24, 0, 28, 28, 28, 28,
  /* 19757 */ 102432, 67, 67, 37139, 37139, 24853, 24853, 0, 0, 2179072, 548, 0, 65820, 65820, 0, 287, 97, 0, 0, 97, 97,
  /* 19778 */ 0, 97, 97, 97, 45, 45, 45, 45, 2033, 45, 67, 67, 67, 67, 0, 0, 97, 97, 97, 97, 45, 45, 67, 67, 0, 369, 0,
  /* 19805 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 978, 0, 546, 70179, 0, 2183168, 0, 0, 552, 0,
  /* 19830 */ 97, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 1013, 67, 67, 67,
  /* 19856 */ 67, 67, 67, 67, 67, 67, 67, 473, 67, 67, 67, 67, 483, 67, 67, 1025, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 19881 */ 67, 67, 67, 67, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 97, 1119, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 19907 */ 97, 97, 1359, 97, 97, 97, 67, 67, 1584, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 497, 67, 67,
  /* 19932 */ 1659, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1667, 45, 45, 45, 45, 45, 169, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 19957 */ 45, 45, 45, 1668, 45, 45, 45, 45, 67, 67, 1694, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 774,
  /* 19982 */ 67, 67, 1713, 97, 97, 97, 97, 97, 97, 97, 0, 97, 97, 1723, 97, 97, 97, 97, 0, 45, 45, 45, 45, 45, 45,
  /* 20007 */ 1538, 45, 45, 45, 45, 45, 1559, 45, 45, 1561, 45, 45, 45, 45, 45, 45, 45, 687, 45, 45, 45, 45, 45, 45, 45,
  /* 20032 */ 45, 448, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 1771, 1772, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97,
  /* 20057 */ 97, 0, 0, 0, 97, 67, 67, 67, 67, 67, 1821, 67, 67, 67, 67, 67, 67, 1827, 67, 67, 67, 0, 0, 0, 0, 0, 0, 97,
  /* 20085 */ 97, 1614, 97, 97, 97, 97, 97, 603, 97, 97, 605, 97, 97, 608, 97, 97, 97, 97, 0, 1532, 45, 45, 45, 45, 45,
  /* 20110 */ 45, 45, 45, 45, 45, 450, 45, 45, 45, 45, 67, 67, 97, 97, 97, 97, 97, 97, 0, 0, 1839, 97, 97, 97, 97, 0, 0,
  /* 20137 */ 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 97, 1883, 97, 1885, 97, 0,
  /* 20162 */ 1888, 0, 97, 97, 0, 97, 97, 1848, 97, 97, 97, 97, 1852, 45, 45, 45, 45, 45, 45, 45, 384, 391, 45, 45, 45,
  /* 20187 */ 45, 45, 45, 45, 385, 45, 45, 45, 45, 45, 45, 45, 45, 1237, 45, 45, 45, 45, 45, 45, 67, 0, 97, 97, 97, 97,
  /* 20213 */ 0, 0, 0, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 1951, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67,
  /* 20240 */ 67, 67, 1963, 97, 2023, 0, 97, 97, 0, 97, 97, 97, 45, 45, 45, 45, 45, 45, 67, 67, 1994, 67, 1995, 67, 67,
  /* 20265 */ 67, 67, 67, 67, 97, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 97, 97, 97, 0, 0, 0, 0, 2220032, 110630, 0,
  /* 20294 */ 0, 0, 114730, 106539, 137, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2793472,
  /* 20307 */ 2805760, 2170880, 2830336, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 20318 */ 2170880, 2170880, 2170880, 2170880, 3031040, 2170880, 3055616, 2170880, 2170880, 67, 67, 37139, 37139,
  /* 20331 */ 24853, 24853, 0, 0, 281, 549, 0, 65820, 65820, 0, 287, 97, 0, 0, 97, 97, 0, 97, 97, 97, 45, 45, 2031,
  /* 20354 */ 2032, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1769, 67, 0, 546, 70179, 549, 549, 0, 0,
  /* 20378 */ 552, 0, 97, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 1858, 45, 641, 0, 0, 0, 0, 41606, 926, 0, 0,
  /* 20404 */ 0, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 456, 67, 0, 0, 0, 1313, 0, 0, 0, 1096, 1319, 0,
  /* 20431 */ 0, 0, 0, 97, 97, 97, 97, 97, 97, 97, 97, 1110, 97, 97, 97, 97, 67, 67, 67, 67, 1301, 1476, 0, 0, 0, 0,
  /* 20457 */ 1307, 1478, 0, 0, 0, 0, 0, 0, 0, 0, 97, 97, 97, 97, 1486, 97, 1487, 97, 1313, 1480, 0, 0, 0, 0, 1319, 0,
  /* 20483 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 566, 97, 97, 97, 97, 97, 97, 67, 67, 67, 1476, 0, 1478, 0, 1480, 0,
  /* 20508 */ 97, 97, 97, 97, 97, 97, 97, 45, 1853, 45, 1855, 45, 45, 45, 45, 53264, 18, 49172, 57366, 26, 8192, 31,
  /* 20530 */ 102432, 0, 110630, 114730, 106539, 0, 0, 225368, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 0, 110630,
  /* 20548 */ 114730, 106539, 0, 0, 32768, 53264, 18, 18, 49172, 163840, 57366, 0, 24, 24, 229376, 0, 28, 28, 28,
  /* 20567 */ 229376, 102432, 0, 0, 0, 0, 2220167, 110630, 0, 0, 0, 114730, 106539, 0, 2171019, 2171019, 2171019,
  /* 20584 */ 2171019, 2592907, 2171019, 2171019, 2171019, 2171019, 2633867, 2171019, 2171019, 2171019, 2171019,
  /* 20595 */ 2171019, 2171019, 2654347, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 20606 */ 2171019, 2171019, 2171019, 3117195, 2171019, 2171019, 2171019, 2171019, 2240641, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 20623 */ 368, 0, 140, 2171019, 2171019, 2171019, 2416779, 2424971, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 20636 */ 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2617483, 2171019, 2171019,
  /* 20647 */ 2642059, 2171019, 2171019, 2171019, 2699403, 2171019, 2728075, 2171019, 2171019, 2171019, 2171019,
  /* 20658 */ 2171019, 2171019, 2171019, 3215499, 2215936, 2215936, 2215936, 2215936, 2215936, 2437120, 2215936,
  /* 20669 */ 2215936, 2171019, 2822283, 2171019, 2171019, 2855051, 2171019, 2171019, 2171019, 2912395, 2171019,
  /* 20680 */ 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 3002507, 2171019, 2171019, 2215936, 2215936,
  /* 20691 */ 2494464, 2215936, 2215936, 2215936, 2171166, 2171166, 2416926, 2425118, 2171166, 2171166, 2171166,
  /* 20702 */ 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166,
  /* 20713 */ 2171166, 2171166, 2576670, 2171166, 2617630, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166,
  /* 20724 */ 2691358, 2171166, 2707742, 2171166, 2715934, 2171166, 2724126, 2765086, 2171166, 2171166, 2797854,
  /* 20735 */ 2171166, 2822430, 2171166, 2171166, 2855198, 2171166, 2171166, 2171166, 2912542, 2171166, 2171166,
  /* 20746 */ 2171166, 2171166, 2171166, 2171166, 2171166, 2793758, 2806046, 2171166, 2830622, 2171166, 2171166,
  /* 20757 */ 2171166, 2171166, 2171166, 2171166, 2171166, 3109150, 2171166, 2171166, 2171166, 2171166, 2171166,
  /* 20768 */ 2171166, 2171166, 2171166, 2171166, 2543902, 2171166, 2171166, 2171166, 2171166, 2171166, 2629918,
  /* 20779 */ 2793611, 2805899, 2171019, 2830475, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 20790 */ 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 0, 546, 0, 0, 2183168, 0,
  /* 20805 */ 0, 552, 0, 2171166, 2171166, 2171166, 2400542, 2171166, 2171166, 2171166, 0, 2171166, 2171166, 2171166, 0,
  /* 20820 */ 2171166, 2920734, 2171166, 2171166, 2171166, 2990366, 2171166, 2171166, 2171166, 2171166, 3117342,
  /* 20831 */ 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166,
  /* 20842 */ 2171166, 0, 53264, 0, 18, 18, 4329472, 2232445, 0, 2240641, 4337664, 2711691, 2171019, 2171019, 2171019,
  /* 20857 */ 2171019, 2171019, 2760843, 2769035, 2789515, 2814091, 2171019, 2171019, 2171019, 2875531, 2904203,
  /* 20868 */ 2171019, 2171019, 3092619, 2171019, 2171019, 3125387, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 20879 */ 2171019, 2171019, 2171019, 2171019, 3199115, 2171019, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 20890 */ 2215936, 2215936, 2215936, 2215936, 2453504, 2457600, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 20901 */ 2215936, 2793472, 2805760, 2215936, 2830336, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 20912 */ 2170880, 2170880, 2170880, 2170880, 2170880, 0, 0, 0, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 20925 */ 2170880, 2170880, 2170880, 2494464, 2170880, 2170880, 2171166, 2171166, 2634014, 2171166, 2171166,
  /* 20936 */ 2171166, 2171166, 2171166, 2171166, 2711838, 2171166, 2171166, 2171166, 2171166, 2171166, 2760990,
  /* 20947 */ 2769182, 2789662, 2814238, 2171166, 2171166, 2171166, 2875678, 2904350, 2171166, 2171166, 2171166,
  /* 20958 */ 2171166, 2171166, 2171166, 2171166, 2171166, 3199262, 2171166, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2379915,
  /* 20975 */ 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2445451, 2171019, 2465931, 2474123,
  /* 20986 */ 2171019, 2171019, 3113099, 2171019, 2171019, 3133579, 2171019, 2171019, 2171019, 3162251, 2171019,
  /* 20997 */ 2171019, 3182731, 3186827, 2171019, 2379776, 2879627, 2171019, 2916491, 2171019, 2171019, 2171019,
  /* 21008 */ 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 3027083, 2171019, 2171019, 3063947, 2699550,
  /* 21019 */ 2171166, 2728222, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2879774, 2171166,
  /* 21030 */ 2916638, 2171166, 2171166, 2171166, 2171166, 2171166, 2609438, 2171166, 2171166, 2171166, 2171166,
  /* 21041 */ 2171166, 2171166, 2654494, 2171166, 2171166, 2171166, 2171166, 2171166, 2445598, 2171166, 2466078,
  /* 21052 */ 2474270, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2523422, 2171019, 2437259, 2171019,
  /* 21063 */ 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2543755,
  /* 21074 */ 2171019, 2171019, 2171019, 2584715, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 21085 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2908299, 2171019,
  /* 21096 */ 2171019, 2936971, 2171019, 2171019, 2986123, 2171019, 2994315, 2171019, 2171019, 3014795, 2171019,
  /* 21107 */ 3059851, 3076235, 3088523, 2171166, 2171166, 2986270, 2171166, 2994462, 2171166, 2171166, 3014942,
  /* 21118 */ 2171166, 3059998, 3076382, 3088670, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 3027230,
  /* 21129 */ 2171166, 2171166, 3064094, 2171166, 2171166, 3113246, 2171166, 2171166, 3133726, 2506891, 2171019,
  /* 21140 */ 2171019, 2171019, 2535563, 2539659, 2171019, 2171019, 2588811, 2171019, 2171019, 2171019, 2171019,
  /* 21151 */ 2171019, 2171019, 2171019, 2691211, 2171019, 2707595, 2171019, 2715787, 2171019, 2723979, 2764939,
  /* 21162 */ 2171019, 2171019, 2797707, 2215936, 2215936, 3170304, 0, 0, 0, 0, 0, 0, 2171166, 2171166, 2171166,
  /* 21177 */ 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2453790, 2457886, 2171166, 2171166, 2171166,
  /* 21188 */ 2486558, 2171166, 2171166, 2507038, 2171166, 2171166, 2171166, 2535710, 2539806, 2171166, 2171166,
  /* 21199 */ 2588958, 2171166, 2171166, 2171166, 2171166, 2515230, 2171166, 2171166, 2171166, 2171166, 2171166,
  /* 21210 */ 2171166, 2171166, 2171166, 2593054, 2171166, 2171166, 2171166, 2171166, 3051806, 2171166, 2171166,
  /* 21221 */ 2171166, 2171166, 2171166, 2171166, 3170590, 0, 2388107, 2392203, 2171019, 2171019, 2433163, 2171019,
  /* 21233 */ 2461835, 2171019, 2171019, 2171019, 2510987, 2171019, 2171019, 2171019, 2171019, 2580619, 2171019,
  /* 21244 */ 2605195, 2637963, 2171019, 2171019, 2171019, 2920587, 2171019, 2171019, 2171019, 2990219, 2171019,
  /* 21255 */ 2171019, 2171019, 2171019, 3051659, 2171019, 2171019, 2171019, 2453643, 2457739, 2171019, 2171019,
  /* 21266 */ 2171019, 2171019, 2171019, 2171019, 2515083, 2171019, 2171019, 2171019, 2171019, 2646155, 2670731,
  /* 21277 */ 2752651, 2756747, 2846859, 2961547, 2171019, 2998411, 2171019, 3010699, 2171019, 2171019, 2687115,
  /* 21288 */ 2748555, 2171019, 2171019, 2171019, 2924683, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 21299 */ 2171019, 3121291, 2171019, 2171019, 2171019, 3170443, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 21310 */ 2215936, 2215936, 2215936, 2486272, 2215936, 2215936, 2506752, 3145867, 3158155, 3166347, 2387968,
  /* 21321 */ 2392064, 2215936, 2215936, 2433024, 2215936, 2461696, 2215936, 2215936, 2215936, 2510848, 2215936,
  /* 21332 */ 2215936, 0, 0, 0, 0, 0, 0, 2179072, 0, 0, 0, 0, 0, 553, 2170880, 2215936, 2215936, 2215936, 2215936,
  /* 21351 */ 2215936, 3121152, 2215936, 2215936, 3145728, 3158016, 3166208, 2388254, 2392350, 2171166, 2171166,
  /* 21362 */ 2433310, 2171166, 2461982, 2171166, 2171166, 2171166, 2511134, 2171166, 2171166, 0, 2171166, 2171166,
  /* 21374 */ 2580766, 2171166, 2605342, 2638110, 2171166, 2171166, 2171166, 2171166, 3031326, 2171166, 3055902,
  /* 21385 */ 2171166, 2171166, 2171166, 2171166, 3092766, 2171166, 2171166, 3125534, 2171166, 2171166, 2171166,
  /* 21396 */ 3162398, 2171166, 2171166, 3182878, 3186974, 2171166, 0, 0, 0, 2171019, 2171019, 2171019, 2171019,
  /* 21409 */ 3109003, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 21420 */ 2215936, 2215936, 2215936, 2400256, 2215936, 2215936, 2215936, 2215936, 2171166, 2687262, 0, 0, 2748702,
  /* 21433 */ 2171166, 2171166, 0, 2171166, 2924830, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166,
  /* 21445 */ 2597150, 2171166, 2621726, 2171166, 2171166, 2642206, 2171166, 2171166, 2171166, 2171166, 3121438,
  /* 21456 */ 2171166, 2171166, 3146014, 3158302, 3166494, 2171019, 2420875, 2429067, 2171019, 2478219, 2171019,
  /* 21467 */ 2171019, 2171019, 2171019, 2547851, 2556043, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 21478 */ 2171019, 2171019, 2171019, 3129483, 2215936, 2171019, 3141771, 2215936, 2420736, 2428928, 2215936,
  /* 21489 */ 2478080, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2646016, 2670592,
  /* 21500 */ 2752512, 2756608, 2846720, 2961408, 2215936, 2998272, 2215936, 3010560, 2215936, 2215936, 2215936,
  /* 21511 */ 3141632, 2171166, 2421022, 2429214, 2171166, 2478366, 2171166, 2171166, 2171166, 2171166, 0, 0, 2171166,
  /* 21524 */ 2171166, 2171166, 2171166, 2646302, 2670878, 0, 0, 0, 0, 37, 110630, 0, 0, 0, 114730, 106539, 0, 45, 45,
  /* 21543 */ 45, 45, 45, 1405, 1406, 45, 45, 45, 45, 1409, 45, 45, 45, 45, 45, 1415, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 21567 */ 45, 45, 1238, 45, 45, 45, 45, 67, 2752798, 2756894, 0, 2847006, 2961694, 2171166, 2998558, 2171166,
  /* 21583 */ 3010846, 2171166, 2171166, 2171166, 3141918, 2171019, 2171019, 2490507, 3129344, 2171166, 2171166,
  /* 21594 */ 2490654, 2171166, 2171166, 2171166, 0, 0, 2547998, 2556190, 2171166, 2171166, 2171166, 0, 0, 0, 0, 37,
  /* 21610 */ 110630, 0, 0, 0, 114730, 106539, 41098, 45, 45, 45, 45, 167, 45, 45, 45, 45, 185, 187, 45, 45, 198, 45,
  /* 21632 */ 45, 0, 2171166, 2171166, 2171166, 2171166, 2171166, 2171166, 3129630, 2171019, 2171019, 2171019, 2171019,
  /* 21645 */ 2171019, 2171019, 2171019, 2171019, 2576523, 2171019, 2171019, 2171019, 2171019, 2171019, 2609291,
  /* 21656 */ 2171019, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 3002368, 2215936, 2215936, 2171166,
  /* 21667 */ 2171166, 2494750, 2171166, 2171166, 0, 0, 0, 0, 37, 110630, 0, 0, 0, 114730, 106539, 41098, 45, 45, 45,
  /* 21686 */ 147, 2584576, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2171166, 2171166, 2171166,
  /* 21698 */ 2171166, 0, 0, 0, 2171166, 2171166, 2171166, 2171166, 0, 0, 0, 2171166, 2171166, 2171166, 3002654,
  /* 21713 */ 2171166, 2171166, 2171019, 2171019, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 21724 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 0, 0, 0, 0, 0, 0, 2175257, 0, 0, 2584862,
  /* 21741 */ 2171166, 2171166, 0, 0, 2171166, 2171166, 2171166, 2171166, 2171166, 2171019, 2441355, 2171019, 2527371,
  /* 21754 */ 2171019, 2601099, 2171019, 2850955, 2171019, 2171019, 2171019, 3022987, 2215936, 2441216, 2215936,
  /* 21765 */ 2527232, 2215936, 2600960, 2215936, 2850816, 2215936, 2215936, 0, 0, 0, 0, 0, 0, 2179072, 0, 0, 0, 0,
  /* 21783 */ 69632, 287, 2170880, 2215936, 3022848, 2171166, 2441502, 2171166, 2527518, 0, 0, 2171166, 2601246,
  /* 21796 */ 2171166, 0, 2851102, 2171166, 2171166, 2171166, 2171166, 2720030, 2744606, 2171166, 2171166, 2171166,
  /* 21808 */ 2834718, 2838814, 2171166, 2908446, 2171166, 2171166, 2937118, 3023134, 2171019, 2519179, 2171019,
  /* 21819 */ 2171019, 2171019, 2171019, 2171019, 2215936, 2519040, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 21830 */ 2171166, 2171166, 2171166, 3215646, 0, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019, 2171019,
  /* 21842 */ 2171019, 2486411, 2171019, 2171019, 2171019, 2629771, 2171019, 2171019, 2171019, 2171019, 2719883,
  /* 21853 */ 2744459, 2171019, 2171019, 2171019, 2834571, 2838667, 2171019, 2519326, 0, 0, 2171166, 2171166, 0,
  /* 21866 */ 2171166, 2171166, 2171166, 2396299, 2171019, 2171019, 2171019, 2171019, 3018891, 2396160, 2215936,
  /* 21877 */ 2215936, 2215936, 2215936, 3018752, 2396446, 0, 0, 2171166, 2171166, 2171166, 2171166, 3019038, 2171019,
  /* 21890 */ 2650251, 2965643, 2171019, 2215936, 2650112, 2965504, 2215936, 0, 0, 2171166, 2650398, 2965790, 2171166,
  /* 21903 */ 2551947, 2171019, 2551808, 2215936, 0, 0, 0, 0, 37, 110630, 0, 0, 0, 114730, 106539, 41098, 45, 45, 144,
  /* 21922 */ 45, 45, 67, 67, 67, 67, 67, 228, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1929, 97, 97, 97, 97, 0, 0, 0,
  /* 21947 */ 2552094, 2171166, 2171019, 2215936, 0, 2171166, 2171019, 2215936, 0, 2171166, 2171019, 2215936, 0,
  /* 21960 */ 2171166, 2977931, 2977792, 2978078, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 97, 1321, 97, 131072, 0, 0,
  /* 21984 */ 0, 0, 0, 0, 0, 0, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 0, 53264, 0, 18, 18, 24, 24, 0,
  /* 22005 */ 28, 28, 0, 140, 0, 2379776, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2445312,
  /* 22019 */ 2170880, 2465792, 2473984, 2170880, 2170880, 2170880, 2584576, 2170880, 2170880, 2170880, 2170880,
  /* 22030 */ 2170880, 2170880, 2170880, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936,
  /* 22041 */ 2215936, 2170880, 2170880, 2170880, 3162112, 2170880, 2170880, 3182592, 3186688, 2170880, 0, 140, 0,
  /* 22054 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 3002368, 2170880, 2170880, 2215936,
  /* 22065 */ 2215936, 2494464, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 3215360, 544, 0, 0, 0, 544, 0,
  /* 22080 */ 546, 0, 0, 0, 546, 0, 0, 2183168, 0, 0, 552, 0, 2170880, 2170880, 2170880, 2400256, 2170880, 2170880,
  /* 22098 */ 2170880, 0, 2170880, 2170880, 2170880, 0, 2170880, 2920448, 2170880, 2170880, 2170880, 2990080, 2170880,
  /* 22111 */ 2170880, 552, 0, 0, 0, 552, 0, 287, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2437120, 2170880,
  /* 22127 */ 2170880, 18, 0, 0, 0, 0, 0, 0, 0, 0, 2220032, 0, 0, 644, 0, 2215936, 2215936, 3170304, 544, 0, 546, 0,
  /* 22149 */ 552, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 3198976, 2170880, 0, 0, 0,
  /* 22164 */ 140, 0, 0, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 249856, 110630, 114730, 106539, 0, 0, 32768,
  /* 22182 */ 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 151640, 53264, 18, 18,
  /* 22200 */ 49172, 0, 57366, 0, 24, 24, 24, 0, 28, 28, 28, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2170880, 2170880,
  /* 22225 */ 2170880, 2416640, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 253952, 110630, 114730, 106539, 0, 0,
  /* 22241 */ 32856, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 192512, 53264, 18,
  /* 22259 */ 18, 49172, 0, 57366, 0, 2232445, 184320, 2232445, 0, 2240641, 2240641, 184320, 2240641, 102432, 0, 0, 0,
  /* 22276 */ 221184, 2220032, 110630, 0, 0, 0, 114730, 106539, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 22291 */ 2170880, 3108864, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 22302 */ 2170880, 2215936, 0, 0, 0, 45056, 0, 0, 0, 0, 0, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 22320 */ 0, 53264, 0, 18, 18, 24, 24, 0, 127, 127, 53264, 18, 49172, 258071, 24, 8192, 28, 102432, 0, 110630,
  /* 22340 */ 114730, 106539, 0, 0, 32768, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0,
  /* 22358 */ 0, 204800, 53264, 18, 49172, 57366, 24, 27, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 0, 53264, 18,
  /* 22377 */ 49172, 57366, 24, 8192, 28, 33, 0, 33, 33, 33, 0, 0, 0, 53264, 18, 18, 49172, 0, 57366, 0, 24, 24, 24,
  /* 22400 */ 16384, 28, 28, 28, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 139, 2170880, 2170880, 2170880, 2416640, 67, 67,
  /* 22422 */ 37139, 37139, 24853, 24853, 0, 70179, 0, 0, 0, 65820, 65820, 369, 287, 97, 0, 0, 97, 97, 0, 97, 97, 97,
  /* 22444 */ 45, 2030, 45, 45, 45, 45, 67, 1573, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1699, 67, 67, 67, 67,
  /* 22468 */ 25403, 546, 70179, 0, 0, 66365, 66365, 552, 0, 97, 97, 97, 97, 97, 97, 97, 97, 1355, 97, 97, 97, 1358, 97,
  /* 22491 */ 97, 97, 641, 0, 0, 0, 925, 41606, 0, 0, 0, 0, 45, 45, 45, 45, 45, 45, 45, 1187, 45, 45, 45, 45, 45, 0,
  /* 22517 */ 1480, 0, 0, 0, 0, 1319, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 592, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 22543 */ 97, 1531, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1680, 45, 45, 45, 641, 0, 924, 0, 925, 41606, 0,
  /* 22568 */ 0, 0, 0, 45, 45, 45, 45, 45, 45, 1186, 45, 45, 45, 45, 45, 45, 67, 67, 37139, 37139, 24853, 24853, 0,
  /* 22591 */ 70179, 282, 0, 0, 65820, 65820, 369, 287, 97, 0, 0, 97, 97, 0, 97, 2028, 97, 45, 45, 45, 45, 45, 45, 67,
  /* 22615 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 1767, 67, 67, 67, 0, 0, 0, 0, 0, 0, 1612, 97, 97, 97, 97, 97, 97, 0,
  /* 22642 */ 1785, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 97, 1790, 97, 0, 0, 2170880, 2170880, 3051520, 2170880,
  /* 22663 */ 2170880, 2170880, 2170880, 2170880, 2170880, 3170304, 241664, 2387968, 2392064, 2170880, 2170880, 2433024,
  /* 22675 */ 53264, 19, 49172, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 274432, 53264, 18, 49172,
  /* 22693 */ 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 270336, 53264, 18, 49172, 57366, 24, 8192,
  /* 22711 */ 28, 102432, 0, 110630, 114730, 106539, 0, 0, 1134711, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 0,
  /* 22729 */ 1126440, 1126440, 1126440, 0, 0, 1126400, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 36, 110630,
  /* 22745 */ 114730, 106539, 0, 0, 217088, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0,
  /* 22763 */ 0, 94, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 96, 53264, 18,
  /* 22782 */ 49172, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 24666, 53264, 18, 18, 49172, 0,
  /* 22800 */ 57366, 0, 24, 24, 24, 126, 28, 28, 28, 28, 102432, 53264, 122, 123, 49172, 0, 57366, 0, 24, 24, 24, 0, 28,
  /* 22823 */ 28, 28, 28, 102432, 2170880, 2170880, 4256099, 0, 0, 0, 0, 0, 0, 0, 0, 2220032, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 22847 */ 1319, 0, 0, 0, 0, 97, 97, 97, 97, 97, 97, 97, 1109, 97, 97, 97, 97, 1113, 132, 0, 0, 0, 37, 110630, 0, 0,
  /* 22873 */ 0, 114730, 106539, 41098, 45, 45, 45, 146, 150, 45, 45, 45, 45, 45, 175, 45, 180, 45, 186, 45, 189, 45,
  /* 22895 */ 45, 203, 67, 256, 67, 67, 270, 67, 67, 0, 37139, 24853, 0, 0, 0, 0, 41098, 65820, 97, 97, 97, 293, 297,
  /* 22918 */ 97, 97, 97, 97, 97, 322, 97, 327, 97, 333, 97, 0, 0, 97, 2026, 0, 2027, 97, 97, 45, 45, 45, 45, 45, 45,
  /* 22943 */ 67, 67, 67, 1685, 67, 67, 67, 67, 67, 67, 67, 1690, 67, 336, 97, 97, 350, 97, 97, 0, 53264, 0, 18, 18, 24,
  /* 22968 */ 24, 356, 28, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 140, 2170880, 2170880, 2170880, 2416640, 2424832, 2170880,
  /* 22989 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 23000 */ 2170880, 2617344, 2170880, 45, 439, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67,
  /* 23022 */ 67, 67, 67, 67, 67, 67, 525, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 23051 */ 0, 97, 97, 97, 97, 622, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1524, 97, 97, 1527, 369, 648, 45,
  /* 23076 */ 45, 45, 45, 45, 45, 45, 45, 45, 659, 45, 45, 45, 45, 408, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 23101 */ 1239, 45, 45, 45, 67, 729, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 23127 */ 67, 67, 67, 762, 67, 746, 67, 67, 67, 67, 67, 67, 67, 67, 67, 759, 67, 67, 67, 67, 0, 0, 0, 1477, 0, 1086,
  /* 23153 */ 0, 0, 0, 1479, 0, 1090, 67, 67, 796, 67, 67, 799, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1291,
  /* 23178 */ 67, 67, 67, 811, 67, 67, 67, 67, 67, 816, 67, 67, 67, 67, 67, 67, 67, 37689, 544, 25403, 546, 70179, 0, 0,
  /* 23202 */ 66365, 66365, 552, 833, 97, 97, 97, 97, 97, 97, 97, 97, 1380, 0, 0, 0, 45, 45, 45, 45, 45, 1185, 45, 45,
  /* 23226 */ 45, 45, 45, 45, 45, 386, 45, 45, 45, 45, 45, 45, 45, 45, 1810, 45, 45, 45, 45, 45, 45, 67, 97, 97, 844,
  /* 23251 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 857, 97, 97, 97, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 23278 */ 97, 45, 45, 45, 97, 97, 97, 894, 97, 97, 897, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0, 0, 1382, 45, 45,
  /* 23304 */ 45, 97, 909, 97, 97, 97, 97, 97, 914, 97, 97, 97, 97, 97, 97, 97, 923, 67, 67, 1079, 67, 67, 67, 67, 67,
  /* 23329 */ 37689, 1085, 25403, 1089, 66365, 1093, 0, 0, 0, 0, 37, 110630, 0, 0, 0, 114730, 106539, 41098, 45, 45, 45,
  /* 23350 */ 148, 1114, 97, 97, 97, 97, 97, 97, 1122, 97, 97, 97, 97, 97, 97, 97, 97, 97, 606, 97, 97, 97, 97, 97, 97,
  /* 23375 */ 97, 97, 97, 97, 1173, 97, 97, 97, 97, 97, 12288, 0, 925, 0, 1179, 0, 0, 0, 0, 37, 110630, 0, 0, 0, 114730,
  /* 23400 */ 106539, 41098, 45, 45, 145, 45, 45, 67, 67, 67, 67, 67, 1762, 67, 67, 67, 1766, 67, 67, 67, 67, 67, 67,
  /* 23423 */ 528, 67, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 0, 1934, 67, 67, 1255, 67, 67, 67, 67, 67,
  /* 23448 */ 67, 67, 67, 67, 67, 67, 67, 67, 1035, 67, 67, 67, 67, 67, 67, 1297, 67, 67, 67, 67, 67, 67, 0, 0, 0, 0, 0,
  /* 23475 */ 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1111, 97, 97, 97, 97, 97, 97, 1327, 97, 97, 97, 97, 97, 97, 97,
  /* 23501 */ 97, 97, 97, 97, 97, 33344, 97, 97, 97, 1335, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 23526 */ 97, 0, 97, 97, 1377, 97, 97, 97, 97, 97, 97, 0, 1179, 0, 45, 45, 45, 45, 670, 45, 45, 45, 45, 45, 45, 45,
  /* 23552 */ 45, 45, 45, 45, 430, 45, 45, 45, 45, 67, 67, 1438, 67, 67, 1442, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 23577 */ 67, 67, 1592, 67, 67, 67, 1451, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1458, 67, 67, 67, 67, 0, 0, 1305,
  /* 23602 */ 0, 0, 0, 0, 0, 1311, 0, 0, 0, 1317, 0, 0, 0, 0, 0, 0, 0, 97, 97, 1322, 97, 97, 1491, 97, 97, 1495, 97, 97,
  /* 23630 */ 97, 97, 97, 97, 97, 97, 97, 97, 0, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1551, 45, 1553, 45,
  /* 23655 */ 1504, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1513, 97, 97, 97, 97, 0, 45, 45, 45, 45, 1536, 45, 45, 45,
  /* 23680 */ 45, 1540, 45, 67, 67, 67, 67, 67, 1585, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1700, 67, 67, 67,
  /* 23705 */ 97, 1648, 97, 97, 97, 97, 97, 97, 97, 97, 0, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1541, 0, 97, 97, 97,
  /* 23731 */ 97, 0, 1940, 0, 97, 97, 97, 97, 97, 97, 45, 45, 2011, 45, 45, 45, 2015, 67, 67, 2017, 67, 67, 67, 2021,
  /* 23755 */ 97, 67, 67, 812, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 37689, 544, 97, 97, 97, 910, 97, 97, 97, 97,
  /* 23780 */ 97, 97, 97, 97, 97, 97, 97, 923, 0, 0, 0, 45, 45, 45, 45, 1184, 45, 45, 45, 45, 1188, 45, 45, 45, 45,
  /* 23805 */ 1414, 45, 45, 45, 1417, 45, 1419, 45, 45, 45, 45, 45, 443, 45, 45, 45, 45, 45, 45, 453, 45, 45, 67, 67,
  /* 23829 */ 67, 67, 1244, 67, 67, 67, 67, 1248, 67, 67, 67, 67, 67, 67, 67, 0, 37139, 24853, 0, 0, 0, 282, 41098,
  /* 23852 */ 65820, 97, 1324, 97, 97, 97, 97, 1328, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0, 930, 45, 45, 45, 45, 97,
  /* 23877 */ 97, 97, 97, 1378, 97, 97, 97, 97, 0, 1179, 0, 45, 45, 45, 45, 671, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 23903 */ 45, 975, 45, 45, 45, 45, 67, 67, 1923, 67, 1925, 67, 67, 1927, 67, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97,
  /* 23928 */ 97, 1985, 45, 45, 45, 45, 45, 45, 1560, 45, 45, 45, 45, 45, 45, 45, 45, 45, 946, 45, 45, 950, 45, 45, 45,
  /* 23953 */ 0, 97, 97, 97, 1939, 0, 0, 0, 97, 1943, 97, 97, 1945, 97, 45, 45, 45, 669, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 23979 */ 45, 45, 45, 45, 990, 45, 45, 45, 67, 257, 67, 67, 67, 67, 67, 0, 37139, 24853, 0, 0, 0, 0, 41098, 65820,
  /* 24003 */ 337, 97, 97, 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 356, 28, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 370,
  /* 24030 */ 2170880, 2170880, 2170880, 2416640, 401, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 24051 */ 67, 67, 459, 461, 67, 67, 67, 67, 67, 67, 67, 67, 475, 67, 480, 67, 67, 67, 67, 67, 67, 1054, 67, 67, 67,
  /* 24076 */ 67, 67, 67, 67, 67, 67, 67, 1698, 67, 67, 67, 67, 67, 484, 67, 67, 487, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 24101 */ 67, 67, 67, 67, 67, 1459, 67, 67, 97, 556, 558, 97, 97, 97, 97, 97, 97, 97, 97, 572, 97, 577, 97, 97, 0,
  /* 24126 */ 0, 1896, 97, 97, 97, 97, 97, 97, 1903, 45, 45, 45, 45, 983, 45, 45, 45, 45, 988, 45, 45, 45, 45, 45, 45,
  /* 24151 */ 1195, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1549, 45, 45, 45, 45, 45, 581, 97, 97, 584, 97, 97, 97, 97,
  /* 24176 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 1153, 97, 97, 369, 0, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 662,
  /* 24202 */ 45, 45, 45, 684, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1004, 45, 45, 45, 67, 67, 67, 749, 67,
  /* 24227 */ 67, 67, 67, 67, 67, 67, 67, 67, 761, 67, 67, 67, 67, 67, 67, 1068, 67, 67, 67, 1071, 67, 67, 67, 67, 1076,
  /* 24252 */ 794, 795, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 0, 544, 97, 97, 97, 97, 847, 97, 97, 97,
  /* 24278 */ 97, 97, 97, 97, 97, 97, 859, 97, 0, 0, 2025, 97, 20480, 97, 97, 2029, 45, 45, 45, 45, 45, 45, 67, 67, 67,
  /* 24303 */ 1575, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1775, 67, 67, 67, 97, 97, 97, 97, 892, 893, 97, 97, 97, 97, 97,
  /* 24328 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 1515, 97, 993, 994, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 24353 */ 45, 45, 45, 992, 67, 67, 67, 1284, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1607, 67, 67, 97,
  /* 24378 */ 1364, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 596, 97, 45, 1556, 1557, 45, 45, 45, 45, 45,
  /* 24403 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 696, 45, 1596, 1597, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 24428 */ 67, 67, 499, 67, 97, 97, 97, 1621, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1346, 97, 97, 97,
  /* 24453 */ 97, 1740, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1678, 45, 45, 45, 45, 45, 67, 97, 97,
  /* 24478 */ 97, 97, 97, 97, 1836, 0, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 1984, 97, 45, 45, 45, 45, 45, 45, 1808, 45,
  /* 24504 */ 45, 45, 45, 45, 45, 45, 45, 67, 739, 67, 67, 67, 67, 67, 744, 45, 45, 1909, 45, 45, 45, 45, 45, 45, 45,
  /* 24529 */ 67, 1917, 67, 1918, 67, 67, 67, 67, 67, 67, 1247, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 532, 67, 67, 67,
  /* 24554 */ 67, 67, 67, 1922, 67, 67, 67, 67, 67, 67, 67, 97, 1930, 97, 1931, 97, 0, 0, 97, 97, 0, 97, 97, 97, 45, 45,
  /* 24580 */ 45, 45, 45, 45, 67, 67, 67, 67, 1576, 67, 67, 67, 67, 1580, 67, 67, 0, 97, 97, 1938, 97, 0, 0, 0, 97, 97,
  /* 24606 */ 97, 97, 97, 97, 45, 45, 45, 699, 45, 45, 45, 704, 45, 45, 45, 45, 45, 45, 45, 45, 987, 45, 45, 45, 45, 45,
  /* 24632 */ 45, 45, 67, 67, 97, 97, 97, 97, 0, 0, 97, 97, 97, 2006, 97, 97, 97, 97, 0, 45, 1533, 45, 45, 45, 45, 45,
  /* 24658 */ 45, 45, 45, 45, 1416, 45, 45, 45, 45, 45, 45, 45, 45, 722, 723, 45, 45, 45, 45, 45, 45, 2045, 67, 67, 67,
  /* 24683 */ 2047, 0, 0, 97, 97, 97, 2051, 45, 45, 67, 67, 0, 0, 0, 0, 925, 41606, 0, 0, 0, 0, 45, 45, 45, 45, 45, 45,
  /* 24710 */ 409, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1957, 45, 67, 67, 67, 67, 67, 1836, 97, 97, 45, 67, 0, 97, 45,
  /* 24735 */ 67, 0, 97, 45, 67, 0, 97, 45, 45, 67, 67, 67, 1761, 67, 67, 67, 1764, 67, 67, 67, 67, 67, 67, 67, 494, 67,
  /* 24761 */ 67, 67, 67, 67, 67, 67, 67, 67, 787, 67, 67, 67, 67, 67, 67, 45, 45, 420, 45, 45, 422, 45, 45, 425, 45,
  /* 24786 */ 45, 45, 45, 45, 45, 45, 387, 45, 45, 45, 45, 397, 45, 45, 45, 67, 460, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 24812 */ 67, 67, 67, 67, 67, 515, 67, 485, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 498, 67, 67, 67, 67,
  /* 24838 */ 67, 97, 0, 2039, 97, 97, 97, 97, 97, 45, 45, 45, 45, 1426, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 24864 */ 1689, 67, 67, 67, 97, 557, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 612, 97, 582, 97, 97,
  /* 24889 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 595, 97, 97, 97, 97, 97, 896, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 24915 */ 97, 97, 885, 97, 97, 97, 97, 97, 45, 939, 45, 45, 45, 45, 943, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 24940 */ 1916, 67, 67, 67, 67, 67, 45, 67, 67, 67, 67, 67, 67, 67, 1015, 67, 67, 67, 67, 1019, 67, 67, 67, 67, 67,
  /* 24965 */ 67, 1271, 67, 67, 67, 67, 67, 67, 1277, 67, 67, 67, 67, 67, 67, 1287, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 24990 */ 67, 804, 67, 67, 67, 67, 67, 1077, 67, 67, 67, 67, 67, 67, 67, 37689, 0, 25403, 0, 66365, 0, 0, 0, 0, 0,
  /* 25015 */ 0, 0, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2437120, 2170880, 2170880, 2170880, 2170880,
  /* 25028 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2543616, 2170880, 2170880, 2170880,
  /* 25039 */ 2170880, 2170880, 2629632, 1169, 97, 1171, 97, 97, 97, 97, 97, 97, 97, 12288, 0, 925, 0, 1179, 0, 0, 0, 0,
  /* 25061 */ 925, 41606, 0, 0, 0, 0, 45, 45, 45, 45, 936, 45, 45, 67, 67, 214, 67, 220, 67, 67, 233, 67, 243, 67, 248,
  /* 25086 */ 67, 67, 67, 67, 67, 67, 1298, 67, 67, 67, 67, 0, 0, 0, 0, 0, 0, 97, 97, 97, 97, 97, 1617, 97, 0, 0, 0, 45,
  /* 25114 */ 45, 45, 1183, 45, 45, 45, 45, 45, 45, 45, 45, 45, 393, 45, 45, 45, 45, 45, 45, 67, 67, 1243, 67, 67, 67,
  /* 25139 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1074, 67, 67, 1281, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 25164 */ 67, 67, 67, 67, 776, 1323, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 907, 45, 1412, 45,
  /* 25189 */ 45, 45, 45, 45, 45, 45, 1418, 45, 45, 45, 45, 45, 45, 686, 45, 45, 45, 690, 45, 45, 695, 45, 45, 67, 67,
  /* 25214 */ 67, 67, 67, 1465, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97, 1712, 97, 97, 97, 97, 1741, 97,
  /* 25239 */ 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 426, 45, 45, 45, 45, 45, 45, 67, 67, 67, 1924, 67, 67, 67, 67,
  /* 25265 */ 67, 97, 97, 97, 97, 97, 0, 0, 97, 97, 1983, 97, 97, 45, 45, 1987, 45, 1988, 45, 0, 97, 97, 97, 97, 0, 0,
  /* 25291 */ 0, 1942, 97, 97, 97, 97, 97, 45, 45, 45, 700, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 711, 45, 45, 153,
  /* 25316 */ 45, 45, 166, 45, 176, 45, 181, 45, 45, 188, 191, 196, 45, 204, 255, 258, 263, 67, 271, 67, 67, 0, 37139,
  /* 25339 */ 24853, 0, 0, 0, 282, 41098, 65820, 97, 97, 97, 294, 97, 300, 97, 97, 313, 97, 323, 97, 328, 97, 97, 335,
  /* 25362 */ 338, 343, 97, 351, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 356, 28, 28, 0, 0, 0, 0, 0, 0, 0, 0, 41098, 0,
  /* 25388 */ 140, 45, 45, 45, 45, 1404, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1411, 67, 67, 486, 67, 67, 67, 67, 67,
  /* 25413 */ 67, 67, 67, 67, 67, 67, 67, 67, 1251, 67, 67, 501, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 513,
  /* 25438 */ 67, 67, 67, 67, 67, 67, 1443, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1263, 67, 67, 67, 67, 67, 97, 97,
  /* 25463 */ 583, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1526, 97, 598, 97, 97, 97, 97, 97, 97, 97,
  /* 25488 */ 97, 97, 97, 97, 97, 610, 97, 97, 0, 97, 97, 1796, 97, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 1744,
  /* 25513 */ 45, 45, 45, 369, 0, 651, 45, 653, 45, 654, 45, 656, 45, 45, 45, 660, 45, 45, 45, 45, 1558, 45, 45, 45, 45,
  /* 25538 */ 45, 45, 45, 45, 1566, 45, 45, 681, 45, 683, 45, 45, 45, 45, 45, 45, 45, 45, 691, 692, 694, 45, 45, 45,
  /* 25562 */ 716, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 709, 45, 45, 712, 45, 714, 45, 45, 45, 718, 45, 45,
  /* 25587 */ 45, 45, 45, 45, 45, 726, 45, 45, 45, 733, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 25613 */ 1691, 67, 67, 747, 67, 67, 67, 67, 67, 67, 67, 67, 67, 760, 67, 67, 67, 0, 0, 0, 0, 0, 0, 97, 1613, 97,
  /* 25639 */ 97, 97, 97, 97, 97, 1509, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 1179, 0, 45, 45, 45, 45, 67, 764, 67, 67,
  /* 25665 */ 67, 67, 768, 67, 770, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 0, 0, 0, 1977, 67, 778, 779, 781,
  /* 25690 */ 67, 67, 67, 67, 67, 67, 788, 789, 67, 67, 792, 793, 67, 67, 67, 813, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 25715 */ 824, 37689, 544, 25403, 546, 70179, 0, 0, 66365, 66365, 552, 0, 836, 97, 838, 97, 839, 97, 841, 97, 97,
  /* 25736 */ 97, 845, 97, 97, 97, 97, 97, 97, 97, 97, 97, 858, 97, 97, 0, 1728, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97,
  /* 25762 */ 97, 97, 97, 97, 45, 1802, 45, 97, 97, 862, 97, 97, 97, 97, 866, 97, 868, 97, 97, 97, 97, 97, 97, 0, 0, 97,
  /* 25788 */ 97, 1788, 97, 97, 97, 0, 0, 97, 97, 876, 877, 879, 97, 97, 97, 97, 97, 97, 886, 887, 97, 97, 890, 891, 97,
  /* 25813 */ 97, 97, 97, 97, 97, 97, 899, 97, 97, 97, 903, 97, 97, 97, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97,
  /* 25839 */ 1646, 97, 97, 97, 97, 911, 97, 97, 97, 97, 97, 97, 97, 97, 97, 922, 923, 45, 955, 45, 957, 45, 45, 45, 45,
  /* 25864 */ 45, 45, 45, 45, 45, 45, 45, 45, 195, 45, 45, 45, 45, 45, 981, 982, 45, 45, 45, 45, 45, 45, 989, 45, 45,
  /* 25889 */ 45, 45, 45, 170, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 411, 45, 45, 45, 45, 45, 67, 1023, 67, 67, 67,
  /* 25914 */ 67, 67, 67, 1031, 67, 1033, 67, 67, 67, 67, 67, 67, 67, 817, 819, 67, 67, 67, 67, 67, 37689, 544, 67,
  /* 25937 */ 1065, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 516, 67, 67, 1078, 67, 67, 1081, 1082, 67,
  /* 25961 */ 67, 37689, 0, 25403, 0, 66365, 0, 0, 0, 0, 0, 0, 0, 0, 2171166, 2171166, 2171166, 2171166, 2171166,
  /* 25980 */ 2437406, 2171166, 2171166, 97, 1115, 97, 1117, 97, 97, 97, 97, 97, 97, 1125, 97, 1127, 97, 97, 97, 0, 97,
  /* 26001 */ 97, 97, 0, 97, 97, 97, 97, 1644, 97, 97, 97, 0, 97, 97, 97, 0, 97, 97, 1642, 97, 97, 97, 97, 97, 97, 625,
  /* 26027 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 316, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1159, 97, 97, 97, 97, 97, 97,
  /* 26053 */ 97, 97, 97, 97, 97, 97, 97, 1502, 97, 97, 97, 97, 97, 1172, 97, 97, 1175, 1176, 97, 97, 12288, 0, 925, 0,
  /* 26077 */ 1179, 0, 0, 0, 0, 925, 41606, 0, 0, 0, 0, 45, 45, 45, 935, 45, 45, 45, 1233, 45, 45, 45, 1236, 45, 45, 45,
  /* 26103 */ 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 1873, 67, 67, 45, 45, 1218, 45, 45, 45, 1223, 45, 45, 45, 45, 45,
  /* 26128 */ 45, 45, 1230, 45, 45, 67, 67, 215, 219, 222, 67, 230, 67, 67, 244, 246, 249, 67, 67, 67, 67, 67, 67, 1882,
  /* 26152 */ 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 97, 97, 45, 1904, 45, 1905, 45, 67, 67, 67, 67, 67, 1258, 67,
  /* 26177 */ 1260, 67, 67, 67, 67, 67, 67, 67, 67, 67, 495, 67, 67, 67, 67, 67, 67, 67, 67, 1283, 67, 67, 67, 67, 67,
  /* 26202 */ 67, 67, 1290, 67, 67, 67, 67, 67, 67, 67, 818, 67, 67, 67, 67, 67, 67, 37689, 544, 67, 67, 1295, 67, 67,
  /* 26226 */ 67, 67, 67, 67, 67, 67, 0, 0, 0, 0, 0, 0, 2174976, 0, 0, 97, 97, 97, 1326, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 26253 */ 97, 97, 97, 97, 97, 1514, 97, 97, 97, 97, 97, 1338, 97, 1340, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 26278 */ 1500, 97, 97, 1503, 97, 1363, 97, 97, 97, 97, 97, 97, 97, 1370, 97, 97, 97, 97, 97, 97, 97, 563, 97, 97,
  /* 26302 */ 97, 97, 97, 97, 578, 97, 1375, 97, 97, 97, 97, 97, 97, 97, 97, 0, 1179, 0, 45, 45, 45, 45, 685, 45, 45,
  /* 26327 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 1003, 45, 45, 45, 45, 67, 67, 67, 1463, 67, 67, 67, 67, 67, 67, 67,
  /* 26352 */ 67, 67, 67, 67, 67, 67, 1778, 97, 97, 97, 97, 97, 1518, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 26377 */ 609, 97, 97, 97, 45, 1542, 45, 45, 45, 45, 45, 45, 45, 1548, 45, 45, 45, 45, 45, 1554, 45, 1570, 1571, 45,
  /* 26401 */ 67, 67, 67, 67, 67, 67, 1578, 67, 67, 67, 67, 67, 67, 67, 1055, 67, 67, 67, 67, 67, 1061, 67, 67, 1582,
  /* 26425 */ 67, 67, 67, 67, 67, 67, 67, 1588, 67, 67, 67, 67, 67, 1594, 67, 67, 67, 67, 67, 97, 2038, 0, 97, 97, 97,
  /* 26450 */ 97, 97, 2044, 45, 45, 45, 995, 45, 45, 45, 45, 1000, 45, 45, 45, 45, 45, 45, 45, 1809, 45, 1811, 45, 45,
  /* 26474 */ 45, 45, 45, 67, 1610, 1611, 67, 1476, 0, 1478, 0, 1480, 0, 97, 97, 97, 97, 97, 97, 1618, 1647, 1649, 97,
  /* 26497 */ 97, 97, 1652, 97, 1654, 1655, 97, 0, 45, 45, 45, 1658, 45, 45, 67, 67, 216, 67, 67, 67, 67, 234, 67, 67,
  /* 26521 */ 67, 67, 252, 254, 1845, 97, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 945, 45, 947, 45, 45,
  /* 26546 */ 45, 45, 45, 67, 67, 67, 67, 67, 1881, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 97, 1902, 45, 45, 45,
  /* 26572 */ 45, 45, 45, 1908, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1921, 67, 67,
  /* 26597 */ 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 0, 0, 0, 97, 97, 0, 97, 1937, 97, 97, 1940, 0, 0, 97, 97, 97,
  /* 26624 */ 97, 97, 97, 1947, 1948, 1949, 45, 45, 45, 1952, 45, 1954, 45, 45, 45, 45, 1959, 1960, 1961, 67, 67, 67,
  /* 26646 */ 67, 67, 67, 1455, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 757, 67, 67, 67, 67, 67, 67, 1964, 67, 1966, 67,
  /* 26671 */ 67, 67, 67, 1971, 1972, 1973, 97, 0, 0, 0, 97, 97, 1104, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 884, 97,
  /* 26696 */ 97, 97, 889, 97, 97, 1978, 97, 0, 0, 1981, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 736, 45, 67, 67, 67,
  /* 26721 */ 67, 67, 67, 67, 67, 67, 67, 67, 1018, 67, 67, 67, 45, 67, 67, 67, 67, 0, 2049, 97, 97, 97, 97, 45, 45, 67,
  /* 26747 */ 67, 0, 0, 0, 0, 925, 41606, 0, 0, 0, 0, 45, 933, 45, 45, 45, 45, 1234, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 26774 */ 45, 67, 97, 97, 288, 97, 97, 97, 97, 97, 97, 317, 97, 97, 97, 97, 97, 97, 0, 0, 97, 1787, 97, 97, 97, 97,
  /* 26800 */ 0, 0, 45, 45, 378, 45, 45, 45, 45, 45, 390, 45, 45, 45, 45, 45, 45, 45, 424, 45, 45, 45, 431, 433, 45, 45,
  /* 26826 */ 45, 67, 1050, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 518, 67, 97, 97, 97, 1144, 97, 97,
  /* 26851 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 632, 97, 97, 97, 97, 97, 97, 97, 1367, 97, 97, 97, 97, 97, 97, 97,
  /* 26877 */ 97, 97, 97, 97, 855, 97, 97, 97, 97, 67, 97, 97, 97, 97, 97, 97, 1837, 0, 97, 97, 97, 97, 97, 0, 0, 0,
  /* 26903 */ 1897, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 1208, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 724, 45, 45,
  /* 26928 */ 45, 45, 45, 97, 2010, 45, 45, 45, 45, 45, 45, 2016, 67, 67, 67, 67, 67, 67, 2022, 45, 2046, 67, 67, 67, 0,
  /* 26953 */ 0, 2050, 97, 97, 97, 45, 45, 67, 67, 0, 0, 0, 0, 925, 41606, 0, 0, 0, 0, 932, 45, 45, 45, 45, 45, 1222,
  /* 26979 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1227, 45, 45, 45, 45, 45, 133, 0, 0, 0, 37, 110630, 0, 0, 0,
  /* 27004 */ 114730, 106539, 41098, 45, 45, 45, 45, 701, 702, 45, 45, 705, 706, 45, 45, 45, 45, 45, 45, 703, 45, 45,
  /* 27026 */ 45, 45, 45, 45, 45, 45, 45, 719, 45, 45, 45, 45, 45, 725, 45, 45, 45, 369, 649, 45, 45, 45, 45, 45, 45,
  /* 27051 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 1216, 25403, 546, 70179, 0, 0, 66365, 66365, 552, 834, 97, 97, 97, 97,
  /* 27074 */ 97, 97, 97, 1342, 97, 97, 97, 97, 97, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97, 1799, 97, 97, 45, 45, 45,
  /* 27100 */ 1569, 45, 45, 45, 1572, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 0, 0, 0, 1306, 0, 67, 67, 67, 1598,
  /* 27125 */ 67, 67, 67, 67, 67, 67, 67, 67, 1606, 67, 67, 1609, 97, 97, 97, 1650, 97, 97, 1653, 97, 97, 97, 0, 45, 45,
  /* 27150 */ 1657, 45, 45, 45, 1206, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1421, 45, 45, 45, 1703, 67, 67,
  /* 27174 */ 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 1711, 97, 97, 0, 1895, 0, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45,
  /* 27200 */ 45, 958, 45, 960, 45, 45, 45, 45, 45, 45, 45, 45, 1913, 45, 45, 1915, 67, 67, 67, 67, 67, 67, 67, 466, 67,
  /* 27225 */ 67, 67, 67, 67, 67, 481, 67, 45, 1749, 45, 45, 45, 45, 45, 45, 45, 45, 1755, 45, 45, 45, 45, 45, 173, 45,
  /* 27250 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 974, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 1773, 67, 67, 67, 67, 67,
  /* 27276 */ 67, 67, 97, 97, 97, 97, 1886, 0, 0, 0, 97, 97, 67, 2035, 2036, 67, 67, 97, 0, 0, 97, 2041, 2042, 97, 97,
  /* 27301 */ 45, 45, 45, 45, 1662, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1397, 45, 45, 45, 45, 151, 45, 45, 45,
  /* 27326 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 437, 205, 45, 67, 67, 67, 218, 67, 67, 67, 67, 67, 67, 67,
  /* 27352 */ 67, 67, 67, 67, 1047, 67, 67, 67, 67, 97, 97, 97, 97, 298, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 27377 */ 870, 97, 97, 97, 97, 97, 97, 97, 97, 352, 97, 0, 53264, 0, 18, 18, 24, 24, 0, 28, 28, 0, 0, 0, 0, 0, 0,
  /* 27404 */ 365, 0, 41098, 0, 140, 45, 45, 45, 45, 45, 1427, 45, 45, 67, 67, 67, 67, 67, 67, 67, 1435, 520, 67, 67,
  /* 27428 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1037, 617, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 27454 */ 97, 97, 97, 97, 923, 45, 1232, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 1919,
  /* 27479 */ 67, 1759, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1021, 45, 154, 45, 162, 45, 45, 45,
  /* 27504 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 964, 45, 45, 45, 206, 45, 67, 67, 67, 67, 221, 67, 229, 67, 67, 67,
  /* 27529 */ 67, 67, 67, 67, 67, 530, 67, 67, 67, 67, 67, 67, 67, 67, 755, 67, 67, 67, 67, 67, 67, 67, 67, 785, 67, 67,
  /* 27555 */ 67, 67, 67, 67, 67, 67, 802, 67, 67, 67, 807, 67, 67, 67, 97, 97, 97, 97, 353, 97, 0, 53264, 0, 18, 18,
  /* 27580 */ 24, 24, 0, 28, 28, 0, 0, 0, 0, 0, 0, 366, 0, 0, 0, 140, 2170880, 2170880, 2170880, 2416640, 402, 45, 45,
  /* 27603 */ 45, 45, 45, 45, 45, 410, 45, 45, 45, 45, 45, 45, 45, 674, 45, 45, 45, 45, 45, 45, 45, 45, 389, 45, 394,
  /* 27628 */ 45, 45, 398, 45, 45, 45, 45, 441, 45, 45, 45, 45, 45, 447, 45, 45, 45, 454, 45, 45, 67, 67, 67, 67, 67,
  /* 27653 */ 67, 67, 67, 67, 67, 67, 1768, 67, 67, 67, 67, 67, 488, 67, 67, 67, 67, 67, 67, 67, 496, 67, 67, 67, 67,
  /* 27678 */ 67, 67, 67, 1774, 67, 67, 67, 67, 67, 97, 97, 97, 97, 0, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 27705 */ 67, 67, 523, 67, 67, 527, 67, 67, 67, 67, 67, 533, 67, 67, 67, 540, 97, 97, 97, 585, 97, 97, 97, 97, 97,
  /* 27730 */ 97, 97, 593, 97, 97, 97, 97, 97, 97, 1784, 0, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 97, 97, 97, 0, 0,
  /* 27757 */ 0, 18, 18, 24, 24, 0, 28, 28, 97, 97, 620, 97, 97, 624, 97, 97, 97, 97, 97, 630, 97, 97, 97, 637, 713, 45,
  /* 27783 */ 45, 45, 45, 45, 45, 721, 45, 45, 45, 45, 45, 45, 45, 45, 1197, 45, 45, 45, 45, 45, 45, 45, 45, 730, 732,
  /* 27808 */ 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1581, 67, 45, 67, 67, 67, 67, 1012, 67, 67,
  /* 27833 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 1059, 67, 67, 67, 67, 67, 1024, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 27858 */ 67, 67, 67, 67, 67, 775, 67, 67, 67, 67, 1066, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 479, 67,
  /* 27883 */ 67, 67, 67, 67, 67, 1080, 67, 67, 67, 67, 37689, 0, 25403, 0, 66365, 0, 0, 0, 0, 0, 0, 0, 287, 0, 0, 0,
  /* 27909 */ 287, 0, 2379776, 2170880, 2170880, 97, 97, 97, 1118, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 920,
  /* 27931 */ 97, 97, 0, 0, 0, 0, 45, 1181, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 432, 45, 45, 45, 45, 45, 45,
  /* 27957 */ 1219, 45, 45, 45, 45, 45, 45, 1226, 45, 45, 45, 45, 45, 45, 959, 45, 45, 45, 45, 45, 45, 45, 45, 45, 184,
  /* 27982 */ 45, 45, 45, 45, 202, 45, 1241, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1266, 67, 1268,
  /* 28007 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1279, 67, 67, 67, 67, 67, 272, 67, 0, 37139, 24853, 0, 0,
  /* 28032 */ 0, 0, 41098, 65820, 67, 67, 67, 67, 67, 1286, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1293, 67, 67, 67, 1296,
  /* 28056 */ 67, 67, 67, 67, 67, 67, 67, 0, 0, 0, 0, 0, 281, 94, 0, 0, 97, 97, 97, 1366, 97, 97, 97, 97, 97, 97, 97,
  /* 28083 */ 97, 97, 1373, 97, 97, 18, 0, 139621, 0, 0, 0, 0, 0, 0, 364, 0, 0, 367, 0, 97, 1376, 97, 97, 97, 97, 97,
  /* 28109 */ 97, 97, 0, 0, 0, 45, 45, 1384, 45, 45, 67, 208, 67, 67, 67, 67, 67, 67, 237, 67, 67, 67, 67, 67, 67, 67,
  /* 28135 */ 1069, 1070, 67, 67, 67, 67, 67, 67, 67, 0, 37140, 24854, 0, 0, 0, 0, 41098, 65821, 45, 1423, 45, 45, 45,
  /* 28158 */ 45, 45, 45, 67, 67, 1431, 67, 67, 67, 67, 67, 67, 67, 1083, 37689, 0, 25403, 0, 66365, 0, 0, 0, 1436, 67,
  /* 28182 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1830, 67, 1452, 1453, 67, 67, 67, 67, 1456, 67,
  /* 28206 */ 67, 67, 67, 67, 67, 67, 67, 67, 771, 67, 67, 67, 67, 67, 67, 1461, 67, 67, 67, 1464, 67, 1466, 67, 67, 67,
  /* 28231 */ 67, 67, 67, 1470, 67, 67, 67, 67, 67, 67, 1587, 67, 67, 67, 67, 67, 67, 67, 67, 1595, 1489, 97, 97, 97,
  /* 28255 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1129, 97, 1505, 1506, 97, 97, 97, 97, 1510, 97, 97, 97,
  /* 28279 */ 97, 97, 97, 97, 97, 97, 1163, 1164, 97, 97, 97, 97, 97, 1516, 97, 97, 97, 1519, 97, 1521, 97, 97, 97, 97,
  /* 28303 */ 97, 97, 1525, 97, 97, 18, 0, 139621, 0, 0, 0, 0, 0, 0, 364, 0, 0, 367, 41606, 67, 67, 67, 67, 67, 1586,
  /* 28328 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1276, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1600, 67, 67, 67,
  /* 28353 */ 67, 67, 67, 67, 67, 67, 67, 67, 1301, 0, 0, 0, 1307, 97, 97, 1620, 97, 97, 97, 97, 97, 97, 97, 1627, 97,
  /* 28378 */ 97, 97, 97, 97, 97, 913, 97, 97, 97, 97, 919, 97, 97, 97, 0, 97, 97, 97, 1781, 97, 97, 0, 0, 97, 97, 97,
  /* 28404 */ 97, 97, 97, 0, 0, 97, 97, 97, 97, 97, 97, 0, 1792, 1860, 45, 1862, 1863, 45, 1865, 45, 67, 67, 67, 67, 67,
  /* 28429 */ 67, 67, 67, 1875, 67, 1877, 1878, 67, 1880, 67, 97, 97, 97, 97, 97, 1887, 0, 1889, 97, 97, 18, 0, 139621,
  /* 28452 */ 0, 0, 0, 0, 0, 0, 364, 237568, 0, 367, 0, 97, 1893, 0, 0, 0, 97, 1898, 1899, 97, 1901, 97, 45, 45, 45, 45,
  /* 28478 */ 45, 2014, 45, 67, 67, 67, 67, 67, 2020, 67, 97, 1989, 45, 1990, 45, 45, 45, 67, 67, 67, 67, 67, 67, 1996,
  /* 28502 */ 67, 1997, 67, 67, 67, 67, 67, 273, 67, 0, 37139, 24853, 0, 0, 0, 0, 41098, 65820, 67, 67, 97, 97, 97, 97,
  /* 28526 */ 0, 0, 97, 97, 2005, 0, 97, 2007, 97, 97, 18, 0, 139621, 0, 0, 0, 642, 0, 133, 364, 0, 0, 367, 41606, 0,
  /* 28551 */ 97, 97, 2056, 2057, 0, 2059, 45, 67, 0, 97, 45, 67, 0, 97, 45, 45, 67, 209, 67, 67, 67, 223, 67, 67, 67,
  /* 28576 */ 67, 67, 67, 67, 67, 67, 786, 67, 67, 67, 791, 67, 67, 45, 45, 940, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 28602 */ 45, 45, 45, 45, 727, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 1016, 67, 67, 67, 67, 67, 67, 67, 67, 37689,
  /* 28627 */ 0, 25403, 0, 66365, 0, 0, 0, 133, 0, 0, 0, 37, 110630, 0, 0, 0, 114730, 106539, 41098, 45, 45, 142, 45,
  /* 28650 */ 45, 67, 210, 67, 67, 67, 225, 67, 67, 239, 67, 67, 67, 250, 67, 67, 67, 67, 67, 464, 67, 67, 67, 67, 67,
  /* 28675 */ 476, 67, 67, 67, 67, 67, 67, 67, 1709, 67, 67, 67, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 97, 97, 1843,
  /* 28701 */ 0, 67, 259, 67, 67, 67, 67, 67, 0, 37139, 24853, 0, 0, 0, 0, 41098, 65820, 97, 97, 289, 97, 97, 97, 303,
  /* 28725 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 901, 97, 97, 97, 97, 97, 339, 97, 97, 97, 97, 97, 0, 53264, 0, 18,
  /* 28751 */ 18, 24, 24, 0, 28, 28, 0, 358, 0, 0, 0, 0, 0, 0, 41098, 0, 140, 45, 45, 45, 45, 45, 1953, 45, 1955, 45,
  /* 28777 */ 45, 45, 67, 67, 67, 67, 67, 67, 67, 1687, 1688, 67, 67, 67, 67, 45, 45, 405, 45, 45, 45, 45, 45, 45, 45,
  /* 28802 */ 45, 45, 45, 45, 45, 45, 45, 1203, 45, 458, 67, 67, 67, 67, 67, 67, 67, 67, 67, 470, 477, 67, 67, 67, 67,
  /* 28827 */ 67, 67, 67, 1970, 97, 97, 97, 1974, 0, 0, 0, 97, 1103, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1372,
  /* 28852 */ 97, 97, 97, 97, 67, 522, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 536, 67, 67, 67, 67, 67, 67, 1696,
  /* 28877 */ 67, 67, 67, 67, 67, 67, 67, 1701, 67, 555, 97, 97, 97, 97, 97, 97, 97, 97, 97, 567, 574, 97, 97, 97, 97,
  /* 28902 */ 97, 301, 97, 309, 97, 97, 97, 97, 97, 97, 97, 97, 97, 900, 97, 97, 97, 905, 97, 97, 97, 619, 97, 97, 97,
  /* 28927 */ 97, 97, 97, 97, 97, 97, 97, 97, 633, 97, 97, 18, 0, 139621, 0, 0, 362, 0, 0, 0, 364, 0, 0, 367, 41606,
  /* 28952 */ 369, 649, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 663, 664, 67, 67, 67, 67, 750, 751, 67, 67, 67,
  /* 28977 */ 67, 758, 67, 67, 67, 67, 67, 67, 67, 1272, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1057, 1058, 67, 67, 67, 67,
  /* 29002 */ 67, 67, 67, 67, 797, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 512, 67, 67, 67, 97, 97, 97, 97, 895,
  /* 29028 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 902, 97, 97, 97, 97, 67, 67, 1051, 67, 67, 67, 67, 67, 67, 67,
  /* 29054 */ 67, 67, 67, 67, 1062, 67, 67, 67, 67, 67, 491, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1302, 0, 0, 0,
  /* 29080 */ 1308, 97, 97, 97, 97, 1145, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1139, 97, 97, 97, 97, 1156, 97,
  /* 29104 */ 97, 97, 97, 97, 97, 1161, 97, 97, 97, 97, 97, 1166, 97, 97, 18, 640, 139621, 0, 641, 0, 0, 0, 0, 364, 0,
  /* 29129 */ 0, 367, 41606, 67, 67, 67, 67, 1257, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 0, 0, 1305, 0, 0, 97, 97,
  /* 29155 */ 1337, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1630, 97, 67, 1474, 67, 67, 0, 0, 0, 0, 0,
  /* 29181 */ 0, 0, 0, 0, 0, 0, 0, 0, 2380062, 2171166, 2171166, 97, 1529, 97, 97, 0, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 29205 */ 45, 45, 45, 1228, 45, 45, 45, 45, 67, 67, 67, 67, 1707, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 0, 0,
  /* 29231 */ 0, 97, 1891, 1739, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1198, 45, 1200, 45, 45, 45,
  /* 29256 */ 45, 97, 97, 1894, 0, 0, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 672, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 29282 */ 45, 45, 45, 1420, 45, 45, 45, 45, 67, 67, 1965, 67, 1967, 67, 67, 67, 97, 97, 97, 97, 0, 1976, 0, 97, 97,
  /* 29307 */ 45, 67, 0, 97, 45, 67, 0, 97, 45, 67, 0, 97, 45, 97, 97, 1979, 0, 0, 97, 1982, 97, 97, 97, 1986, 45, 45,
  /* 29333 */ 45, 45, 45, 735, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1770, 67, 67, 2000, 97, 97,
  /* 29358 */ 97, 2002, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 1798, 97, 97, 97, 45, 45, 45, 2034, 67, 67, 67, 67,
  /* 29383 */ 97, 0, 0, 2040, 97, 97, 97, 97, 45, 45, 45, 45, 1752, 45, 45, 45, 1753, 1754, 45, 45, 45, 45, 45, 45, 383,
  /* 29408 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 675, 45, 45, 45, 45, 45, 45, 438, 45, 45, 45, 45, 45, 445, 45, 45, 45,
  /* 29434 */ 45, 45, 45, 45, 45, 67, 1430, 67, 67, 67, 67, 67, 67, 67, 67, 67, 524, 67, 67, 67, 67, 67, 531, 67, 67,
  /* 29459 */ 67, 67, 67, 67, 67, 67, 37689, 0, 25403, 0, 66365, 0, 0, 1096, 97, 97, 97, 621, 97, 97, 97, 97, 97, 628,
  /* 29483 */ 97, 97, 97, 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 356, 28, 28, 665, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 29509 */ 676, 45, 45, 45, 45, 45, 942, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 707, 708, 45, 45, 45, 45, 763, 67,
  /* 29534 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 809, 810, 67, 67, 67, 67, 783, 67, 67, 67, 67, 67,
  /* 29560 */ 67, 67, 67, 67, 67, 67, 0, 1303, 0, 0, 0, 97, 861, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 29587 */ 613, 97, 45, 45, 956, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1215, 45, 67, 67, 67, 67,
  /* 29612 */ 1027, 67, 67, 67, 67, 1032, 67, 67, 67, 67, 67, 67, 67, 67, 37689, 0, 25403, 0, 66365, 0, 0, 1097, 1064,
  /* 29635 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1075, 67, 1098, 0, 0, 97, 97, 97, 97, 97, 97,
  /* 29661 */ 97, 97, 97, 97, 97, 97, 97, 331, 97, 97, 97, 97, 1158, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 29687 */ 594, 97, 97, 1309, 0, 0, 0, 1315, 0, 0, 0, 0, 0, 0, 0, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 29715 */ 97, 97, 1374, 97, 45, 45, 1543, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1240, 67, 67,
  /* 29739 */ 1583, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1252, 67, 97, 97, 97, 1635, 97, 97, 97, 0,
  /* 29764 */ 97, 97, 97, 97, 97, 97, 97, 97, 1800, 97, 45, 45, 45, 97, 97, 1793, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 29789 */ 97, 45, 45, 45, 1743, 45, 45, 45, 1746, 45, 0, 97, 97, 97, 97, 97, 1851, 97, 45, 45, 45, 45, 1856, 45, 45,
  /* 29814 */ 45, 45, 1864, 45, 45, 67, 67, 1869, 67, 67, 67, 67, 1874, 67, 0, 97, 97, 45, 67, 2058, 97, 45, 67, 0, 97,
  /* 29839 */ 45, 67, 0, 97, 45, 45, 67, 211, 67, 67, 67, 67, 67, 67, 240, 67, 67, 67, 67, 67, 67, 67, 1444, 67, 67, 67,
  /* 29865 */ 67, 67, 67, 67, 67, 67, 509, 67, 67, 67, 67, 67, 67, 67, 67, 67, 268, 67, 67, 67, 0, 37139, 24853, 0, 0,
  /* 29890 */ 0, 0, 41098, 65820, 97, 97, 290, 97, 97, 97, 305, 97, 97, 319, 97, 97, 97, 330, 97, 97, 18, 640, 139621,
  /* 29913 */ 0, 641, 0, 0, 0, 0, 364, 0, 643, 367, 41606, 97, 97, 348, 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 0, 28,
  /* 29939 */ 28, 139621, 0, 0, 0, 0, 364, 0, 367, 41098, 369, 140, 45, 45, 45, 45, 380, 45, 45, 45, 45, 45, 45, 395,
  /* 29963 */ 45, 45, 45, 400, 369, 0, 45, 45, 45, 45, 45, 45, 45, 45, 658, 45, 45, 45, 45, 45, 972, 45, 45, 45, 45, 45,
  /* 29989 */ 45, 45, 45, 45, 45, 427, 45, 45, 45, 45, 45, 745, 67, 67, 67, 67, 67, 67, 67, 67, 756, 67, 67, 67, 67, 67,
  /* 30015 */ 67, 67, 67, 37689, 1086, 25403, 1090, 66365, 1094, 0, 0, 97, 843, 97, 97, 97, 97, 97, 97, 97, 97, 854, 97,
  /* 30038 */ 97, 97, 97, 97, 97, 1121, 97, 97, 97, 97, 1126, 97, 97, 97, 97, 45, 980, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 30063 */ 45, 45, 45, 45, 45, 45, 45, 1400, 45, 67, 67, 67, 1011, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 0,
  /* 30088 */ 1304, 0, 0, 0, 1190, 45, 45, 1193, 1194, 45, 45, 45, 45, 45, 1199, 45, 1201, 45, 45, 45, 45, 1911, 45, 45,
  /* 30112 */ 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 1579, 67, 67, 67, 67, 45, 1205, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 30137 */ 1211, 45, 45, 45, 45, 45, 984, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1550, 45, 45, 45, 45, 45, 1217,
  /* 30162 */ 45, 45, 45, 45, 45, 45, 1225, 45, 45, 45, 45, 1229, 45, 45, 45, 1388, 45, 45, 45, 45, 45, 45, 1396, 45,
  /* 30186 */ 45, 45, 45, 45, 444, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 1574, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 30212 */ 67, 1590, 67, 67, 67, 67, 67, 1254, 67, 67, 67, 67, 67, 1259, 67, 1261, 67, 67, 67, 67, 1265, 67, 67, 67,
  /* 30236 */ 67, 67, 67, 1708, 67, 67, 67, 67, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 97, 97, 0, 0, 67, 67, 67, 67,
  /* 30263 */ 1285, 67, 67, 67, 67, 1289, 67, 67, 67, 67, 67, 67, 67, 67, 37689, 1087, 25403, 1091, 66365, 1095, 0, 0,
  /* 30285 */ 97, 97, 97, 97, 1339, 97, 1341, 97, 97, 97, 97, 1345, 97, 97, 97, 97, 97, 561, 97, 97, 97, 97, 97, 573,
  /* 30309 */ 97, 97, 97, 97, 97, 97, 1717, 97, 0, 97, 97, 97, 97, 97, 97, 97, 591, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 30335 */ 1329, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1351, 97, 97, 97, 97, 97, 97, 1357, 97, 97, 97, 97, 97, 588,
  /* 30360 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 568, 97, 97, 97, 97, 97, 97, 97, 1365, 97, 97, 97, 97, 1369, 97,
  /* 30385 */ 97, 97, 97, 97, 97, 97, 97, 97, 1356, 97, 97, 97, 97, 97, 97, 45, 45, 1403, 45, 45, 45, 45, 45, 45, 45,
  /* 30410 */ 45, 45, 45, 45, 45, 45, 45, 1399, 45, 45, 45, 1413, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 30435 */ 45, 1669, 45, 1422, 45, 45, 1425, 45, 45, 1428, 45, 1429, 67, 67, 67, 67, 67, 67, 67, 67, 1468, 67, 67,
  /* 30458 */ 67, 67, 67, 67, 67, 67, 529, 67, 67, 67, 67, 67, 67, 539, 67, 67, 1475, 67, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 30486 */ 0, 0, 140, 2170880, 2170880, 2170880, 2416640, 97, 97, 1530, 97, 0, 45, 45, 1534, 45, 45, 45, 45, 45, 45,
  /* 30507 */ 45, 45, 1956, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1599, 67, 67, 1601, 67, 67, 67, 67, 67, 67, 67,
  /* 30532 */ 67, 67, 803, 67, 67, 67, 67, 67, 67, 1632, 97, 1634, 0, 97, 97, 97, 1640, 97, 97, 97, 1643, 97, 97, 1645,
  /* 30556 */ 97, 97, 97, 97, 97, 912, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0, 0, 45, 45, 45, 45, 45, 45, 1660, 1661,
  /* 30582 */ 45, 45, 45, 45, 1665, 1666, 45, 45, 45, 45, 45, 1670, 1692, 1693, 67, 67, 67, 67, 67, 1697, 67, 67, 67,
  /* 30605 */ 67, 67, 67, 67, 1702, 97, 97, 1714, 1715, 97, 97, 97, 97, 0, 1721, 1722, 97, 97, 97, 97, 97, 97, 1353, 97,
  /* 30629 */ 97, 97, 97, 97, 97, 97, 97, 1362, 1726, 97, 0, 0, 97, 97, 97, 0, 97, 97, 97, 1734, 97, 97, 97, 97, 97,
  /* 30654 */ 848, 849, 97, 97, 97, 97, 856, 97, 97, 97, 97, 97, 354, 0, 53264, 0, 18, 18, 24, 24, 0, 28, 28, 45, 45,
  /* 30679 */ 1750, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1681, 45, 0, 1846, 97, 97, 97, 97, 97, 97,
  /* 30704 */ 45, 45, 1854, 45, 45, 45, 45, 1859, 67, 67, 67, 1879, 67, 67, 97, 97, 1884, 97, 97, 0, 0, 0, 97, 97, 97,
  /* 30729 */ 1105, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1344, 97, 97, 97, 1347, 97, 1892, 97, 0, 0, 0, 97, 97, 97,
  /* 30754 */ 1900, 97, 97, 45, 45, 45, 45, 45, 997, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1002, 45, 45, 1005, 1006,
  /* 30778 */ 45, 67, 67, 67, 67, 67, 1926, 67, 67, 1928, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97,
  /* 30804 */ 97, 1737, 97, 0, 97, 97, 97, 97, 0, 0, 0, 97, 97, 1944, 97, 97, 1946, 45, 45, 45, 1544, 45, 45, 45, 45,
  /* 30829 */ 45, 45, 45, 45, 45, 45, 45, 45, 190, 45, 45, 45, 152, 155, 45, 163, 45, 45, 177, 179, 182, 45, 45, 45,
  /* 30853 */ 193, 197, 45, 45, 45, 1672, 45, 45, 45, 45, 45, 1677, 45, 1679, 45, 45, 45, 45, 996, 45, 45, 45, 45, 45,
  /* 30877 */ 45, 45, 45, 45, 45, 45, 1212, 45, 45, 45, 45, 67, 260, 264, 67, 67, 67, 67, 0, 37139, 24853, 0, 0, 0, 0,
  /* 30902 */ 41098, 65820, 97, 97, 97, 295, 299, 302, 97, 310, 97, 97, 324, 326, 329, 97, 97, 97, 0, 97, 97, 1639, 0,
  /* 30925 */ 1641, 97, 97, 97, 97, 97, 97, 97, 97, 1511, 97, 97, 97, 97, 97, 97, 97, 97, 1523, 97, 97, 97, 97, 97, 97,
  /* 30950 */ 97, 97, 1719, 97, 97, 97, 97, 97, 97, 97, 97, 1720, 97, 97, 97, 97, 97, 97, 97, 312, 97, 97, 97, 97, 97,
  /* 30975 */ 97, 97, 97, 1123, 97, 97, 97, 97, 97, 97, 97, 340, 344, 97, 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 0,
  /* 31000 */ 28, 28, 139621, 0, 0, 0, 0, 364, 0, 367, 41098, 369, 140, 45, 45, 373, 375, 419, 45, 45, 45, 45, 45, 45,
  /* 31024 */ 45, 45, 45, 428, 45, 45, 435, 45, 45, 45, 1751, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1410, 45,
  /* 31049 */ 45, 45, 67, 67, 67, 505, 67, 67, 67, 67, 67, 67, 67, 67, 67, 514, 67, 67, 67, 67, 67, 67, 1969, 67, 97,
  /* 31074 */ 97, 97, 97, 0, 0, 0, 97, 97, 45, 67, 0, 97, 45, 67, 0, 97, 2064, 2065, 0, 2066, 45, 521, 67, 67, 67, 67,
  /* 31100 */ 67, 67, 67, 67, 67, 67, 534, 67, 67, 67, 67, 67, 67, 465, 67, 67, 67, 474, 67, 67, 67, 67, 67, 67, 67,
  /* 31125 */ 1467, 67, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 1933, 0, 97, 97, 97, 602, 97, 97, 97, 97,
  /* 31150 */ 97, 97, 97, 97, 97, 611, 97, 97, 18, 640, 139621, 358, 641, 0, 0, 0, 0, 364, 0, 0, 367, 0, 618, 97, 97,
  /* 31175 */ 97, 97, 97, 97, 97, 97, 97, 97, 631, 97, 97, 97, 97, 97, 881, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 569,
  /* 31201 */ 97, 97, 97, 97, 97, 369, 0, 45, 652, 45, 45, 45, 45, 45, 657, 45, 45, 45, 45, 45, 45, 1235, 45, 45, 45,
  /* 31226 */ 45, 45, 45, 45, 45, 67, 67, 67, 1432, 67, 67, 67, 67, 67, 67, 67, 766, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 31251 */ 773, 67, 67, 67, 0, 1305, 0, 1311, 0, 1317, 97, 97, 97, 97, 97, 97, 97, 1624, 97, 97, 97, 97, 97, 97, 97,
  /* 31276 */ 97, 0, 97, 97, 97, 1724, 97, 97, 97, 777, 67, 67, 782, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 31301 */ 535, 67, 67, 67, 67, 67, 67, 67, 814, 67, 67, 67, 67, 67, 67, 67, 67, 67, 37689, 544, 25403, 546, 70179,
  /* 31324 */ 0, 0, 66365, 66365, 552, 0, 97, 837, 97, 97, 97, 97, 97, 97, 1496, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 31349 */ 918, 97, 97, 97, 97, 0, 842, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1168, 97, 97, 97,
  /* 31375 */ 97, 864, 97, 97, 97, 97, 97, 97, 97, 97, 871, 97, 97, 97, 0, 1637, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97,
  /* 31401 */ 97, 97, 97, 1801, 45, 45, 97, 875, 97, 97, 880, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1151, 1152,
  /* 31425 */ 97, 97, 97, 67, 67, 67, 1040, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 790, 67, 67, 67, 1180, 0,
  /* 31450 */ 649, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 200, 45, 45, 67, 67, 67, 1454, 67, 67, 67, 67,
  /* 31475 */ 67, 67, 67, 67, 67, 67, 67, 67, 806, 67, 67, 67, 0, 0, 0, 1481, 0, 1094, 0, 0, 97, 1483, 97, 97, 97, 97,
  /* 31501 */ 97, 97, 304, 97, 97, 318, 97, 97, 97, 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 0, 28, 28, 97, 97, 97,
  /* 31526 */ 1507, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1332, 97, 97, 97, 1619, 97, 97, 97, 97, 97, 97, 97,
  /* 31551 */ 97, 97, 97, 97, 97, 97, 97, 97, 1631, 97, 1633, 97, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 31577 */ 1381, 0, 0, 45, 45, 45, 45, 97, 97, 1727, 0, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 626, 97, 97,
  /* 31603 */ 97, 97, 97, 97, 636, 45, 45, 1760, 67, 67, 67, 67, 67, 67, 67, 1765, 67, 67, 67, 67, 67, 67, 67, 1299, 67,
  /* 31628 */ 67, 67, 0, 0, 0, 0, 0, 0, 97, 97, 97, 97, 1616, 97, 97, 1803, 45, 45, 45, 45, 1807, 45, 45, 45, 45, 45,
  /* 31654 */ 1813, 45, 45, 45, 67, 67, 1684, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 822, 67, 67, 37689, 544, 67,
  /* 31678 */ 67, 1818, 67, 67, 67, 67, 1822, 67, 67, 67, 67, 67, 1828, 67, 67, 67, 67, 67, 97, 0, 0, 97, 97, 97, 97,
  /* 31703 */ 97, 45, 45, 45, 2012, 2013, 45, 45, 67, 67, 67, 2018, 2019, 67, 67, 97, 67, 97, 97, 97, 1833, 97, 97, 0,
  /* 31727 */ 0, 97, 97, 1840, 97, 97, 0, 0, 97, 97, 97, 0, 97, 97, 1733, 97, 1735, 97, 97, 97, 0, 97, 97, 97, 1849, 97,
  /* 31753 */ 97, 97, 45, 45, 45, 45, 45, 1857, 45, 45, 45, 1910, 45, 1912, 45, 45, 1914, 45, 67, 67, 67, 67, 67, 67,
  /* 31777 */ 67, 67, 67, 67, 1017, 67, 67, 1020, 67, 45, 1861, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 1872, 67, 67,
  /* 31801 */ 67, 67, 67, 67, 752, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1446, 67, 67, 67, 67, 67, 1876, 67, 67, 67,
  /* 31826 */ 67, 67, 97, 97, 97, 97, 97, 0, 0, 0, 1890, 97, 97, 97, 97, 97, 1134, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 31852 */ 97, 570, 97, 97, 97, 97, 580, 1935, 97, 97, 97, 97, 0, 0, 0, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 1906,
  /* 31878 */ 45, 67, 67, 67, 67, 2048, 0, 97, 97, 97, 97, 45, 45, 67, 67, 0, 0, 0, 0, 925, 41606, 0, 0, 0, 931, 45, 45,
  /* 31905 */ 45, 45, 45, 45, 1674, 45, 1676, 45, 45, 45, 45, 45, 45, 45, 446, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67,
  /* 31930 */ 67, 1871, 67, 67, 67, 67, 0, 97, 97, 45, 67, 0, 97, 2060, 2061, 0, 2063, 45, 67, 0, 97, 45, 45, 156, 45,
  /* 31955 */ 45, 45, 45, 45, 45, 45, 45, 45, 192, 45, 45, 45, 45, 1673, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 31980 */ 429, 45, 45, 45, 45, 67, 67, 67, 269, 67, 67, 67, 0, 37139, 24853, 0, 0, 0, 0, 41098, 65820, 97, 97, 349,
  /* 32004 */ 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 0, 28, 28, 139621, 0, 0, 0, 0, 364, 0, 367, 41098, 369, 140, 45,
  /* 32029 */ 45, 374, 45, 45, 67, 67, 213, 217, 67, 67, 67, 67, 67, 242, 67, 247, 67, 253, 45, 45, 698, 45, 45, 45, 45,
  /* 32054 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 399, 45, 45, 0, 0, 0, 0, 925, 41606, 0, 929, 0, 0, 45, 45, 45, 45, 45,
  /* 32081 */ 45, 1391, 45, 45, 1395, 45, 45, 45, 45, 45, 45, 423, 45, 45, 45, 45, 45, 45, 45, 436, 45, 67, 67, 67, 67,
  /* 32106 */ 1041, 67, 1043, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1776, 67, 67, 97, 97, 97, 1099, 0, 0, 97, 97, 97,
  /* 32131 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 888, 97, 97, 97, 1131, 97, 97, 97, 97, 1135, 97, 1137, 97, 97, 97,
  /* 32156 */ 97, 97, 97, 97, 1497, 97, 97, 97, 97, 97, 97, 97, 97, 97, 883, 97, 97, 97, 97, 97, 97, 1310, 0, 0, 0,
  /* 32181 */ 1316, 0, 0, 0, 0, 1100, 0, 0, 0, 97, 97, 97, 97, 97, 1107, 97, 97, 97, 97, 97, 97, 97, 97, 1343, 97, 97,
  /* 32207 */ 97, 97, 97, 97, 1348, 0, 0, 1317, 0, 0, 0, 0, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1112, 97, 45,
  /* 32234 */ 1804, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 1868, 67, 1870, 67, 67, 67, 67, 67, 1817,
  /* 32258 */ 67, 67, 1819, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 823, 67, 37689, 544, 67, 97, 1832, 97, 97,
  /* 32282 */ 1834, 97, 0, 0, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 0, 1732, 97, 97, 97, 97, 97, 97, 97, 850, 97, 97,
  /* 32308 */ 97, 97, 97, 97, 97, 97, 97, 1177, 0, 0, 925, 0, 0, 0, 0, 97, 97, 97, 97, 0, 0, 1941, 97, 97, 97, 97, 97,
  /* 32335 */ 97, 45, 45, 45, 1991, 1992, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1998, 134, 0, 0, 0, 37, 110630, 0, 0,
  /* 32360 */ 0, 114730, 106539, 41098, 45, 45, 45, 45, 941, 45, 45, 944, 45, 45, 45, 45, 45, 45, 952, 45, 45, 207, 67,
  /* 32383 */ 67, 67, 67, 67, 226, 67, 67, 67, 67, 67, 67, 67, 67, 67, 820, 67, 67, 67, 67, 37689, 544, 369, 650, 45,
  /* 32407 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1682, 25403, 546, 70179, 0, 0, 66365, 66365, 552,
  /* 32430 */ 835, 97, 97, 97, 97, 97, 97, 97, 1522, 97, 97, 97, 97, 97, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 1725,
  /* 32455 */ 67, 67, 67, 1695, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1034, 67, 1036, 67, 67, 67, 265, 67, 67,
  /* 32480 */ 67, 67, 0, 37139, 24853, 0, 0, 0, 0, 41098, 65820, 97, 97, 97, 296, 97, 97, 97, 97, 314, 97, 97, 97, 97,
  /* 32504 */ 332, 334, 97, 97, 97, 97, 97, 1146, 1147, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1626, 97, 97, 97, 97,
  /* 32528 */ 97, 97, 345, 97, 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 0, 28, 28, 139621, 0, 0, 0, 0, 364, 0, 367,
  /* 32553 */ 41098, 369, 140, 45, 372, 45, 45, 45, 1220, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1213, 45, 45,
  /* 32577 */ 45, 45, 404, 406, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 434, 45, 45, 45, 440, 45, 45, 45,
  /* 32602 */ 45, 45, 45, 45, 45, 451, 452, 45, 45, 45, 67, 1683, 67, 67, 67, 1686, 67, 67, 67, 67, 67, 67, 67, 0,
  /* 32626 */ 37139, 24853, 0, 0, 0, 0, 41098, 65820, 67, 67, 67, 67, 490, 492, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 32650 */ 67, 1447, 67, 67, 1450, 67, 67, 67, 67, 67, 526, 67, 67, 67, 67, 67, 67, 67, 67, 537, 538, 67, 67, 67, 67,
  /* 32675 */ 67, 506, 67, 67, 508, 67, 67, 511, 67, 67, 67, 67, 0, 1476, 0, 0, 0, 0, 0, 1478, 0, 0, 0, 0, 0, 0, 0, 0,
  /* 32703 */ 97, 97, 1484, 97, 97, 97, 97, 97, 97, 865, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1499, 97, 97, 97, 97,
  /* 32728 */ 97, 97, 97, 97, 97, 587, 589, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 629, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 32754 */ 97, 623, 97, 97, 97, 97, 97, 97, 97, 97, 634, 635, 97, 97, 97, 97, 97, 1160, 97, 97, 97, 97, 97, 97, 97,
  /* 32779 */ 97, 97, 97, 97, 1628, 97, 97, 97, 97, 369, 0, 45, 45, 45, 45, 45, 655, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 32804 */ 999, 45, 1001, 45, 45, 45, 45, 45, 45, 45, 45, 715, 45, 45, 45, 720, 45, 45, 45, 45, 45, 45, 45, 45, 728,
  /* 32829 */ 25403, 546, 70179, 0, 0, 66365, 66365, 552, 0, 97, 97, 97, 97, 97, 840, 97, 97, 97, 97, 97, 1174, 97, 97,
  /* 32852 */ 97, 97, 0, 0, 925, 0, 0, 0, 0, 0, 0, 0, 1100, 97, 97, 97, 97, 97, 97, 97, 97, 627, 97, 97, 97, 97, 97, 97,
  /* 32880 */ 97, 938, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 680, 45, 968, 45, 970, 45, 973, 45,
  /* 32905 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 962, 45, 45, 45, 45, 45, 979, 45, 45, 45, 45, 45, 985, 45, 45, 45, 45,
  /* 32931 */ 45, 45, 45, 45, 45, 1224, 45, 45, 45, 45, 45, 45, 45, 45, 688, 45, 45, 45, 45, 45, 45, 45, 1007, 1008, 67,
  /* 32956 */ 67, 67, 67, 67, 1014, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1045, 67, 67, 67, 67, 67, 67, 67, 1038, 67, 67,
  /* 32981 */ 67, 67, 67, 67, 1044, 67, 1046, 67, 1049, 67, 67, 67, 67, 67, 67, 800, 67, 67, 67, 67, 67, 67, 808, 67,
  /* 33005 */ 67, 0, 0, 0, 1102, 97, 97, 97, 97, 97, 1108, 97, 97, 97, 97, 97, 97, 306, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 33031 */ 97, 97, 1371, 97, 97, 97, 97, 97, 97, 97, 97, 1132, 97, 97, 97, 97, 97, 97, 1138, 97, 1140, 97, 1143, 97,
  /* 33055 */ 97, 97, 97, 97, 1352, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 869, 97, 97, 97, 97, 97, 45, 1191, 45, 45,
  /* 33080 */ 45, 45, 45, 1196, 45, 45, 45, 45, 45, 45, 45, 45, 1407, 45, 45, 45, 45, 45, 45, 45, 45, 986, 45, 45, 45,
  /* 33105 */ 45, 45, 45, 991, 45, 67, 67, 67, 1256, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1048, 67, 67, 67,
  /* 33130 */ 97, 1336, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 615, 97, 1386, 45, 1387, 45, 45, 45, 45,
  /* 33155 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 455, 45, 457, 45, 45, 1424, 45, 45, 45, 45, 45, 67, 67, 67, 67, 1433,
  /* 33180 */ 67, 1434, 67, 67, 67, 67, 67, 767, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1591, 67, 1593, 67, 67, 45,
  /* 33205 */ 45, 1805, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1814, 45, 45, 1816, 67, 67, 67, 67, 1820, 67, 67, 67, 67,
  /* 33229 */ 67, 67, 67, 67, 67, 1829, 67, 67, 67, 67, 67, 815, 67, 67, 67, 67, 821, 67, 67, 67, 37689, 544, 67, 1831,
  /* 33253 */ 97, 97, 97, 97, 1835, 0, 0, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 1731, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 33279 */ 97, 853, 97, 97, 97, 97, 97, 97, 0, 97, 97, 97, 97, 1850, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 1547,
  /* 33304 */ 45, 45, 45, 45, 45, 45, 45, 45, 1664, 45, 45, 45, 45, 45, 45, 45, 45, 961, 45, 45, 45, 45, 965, 45, 967,
  /* 33329 */ 1907, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 1920, 0, 1936, 97, 97, 97, 0, 0, 0, 97, 97,
  /* 33355 */ 97, 97, 97, 97, 45, 45, 67, 67, 67, 67, 67, 67, 1763, 67, 67, 67, 67, 67, 67, 67, 67, 1056, 67, 67, 67,
  /* 33380 */ 67, 67, 67, 67, 67, 1273, 67, 67, 67, 67, 67, 67, 67, 67, 1457, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97,
  /* 33405 */ 97, 97, 0, 0, 28672, 97, 45, 67, 67, 67, 67, 0, 0, 97, 97, 97, 97, 45, 45, 67, 67, 2054, 97, 97, 291, 97,
  /* 33431 */ 97, 97, 97, 97, 97, 320, 97, 97, 97, 97, 97, 97, 307, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 12288, 0,
  /* 33456 */ 925, 926, 1179, 0, 45, 377, 45, 45, 45, 381, 45, 45, 392, 45, 45, 396, 45, 45, 45, 45, 971, 45, 45, 45,
  /* 33480 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 1756, 45, 45, 45, 67, 67, 67, 67, 463, 67, 67, 67, 467, 67, 67, 478,
  /* 33505 */ 67, 67, 482, 67, 67, 67, 67, 67, 1028, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1469, 67, 67, 1472,
  /* 33530 */ 67, 502, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1460, 67, 97, 97, 97, 97, 560, 97, 97,
  /* 33555 */ 97, 564, 97, 97, 575, 97, 97, 579, 97, 97, 97, 97, 97, 1368, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0,
  /* 33581 */ 925, 0, 0, 930, 97, 599, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 872, 97, 45, 666, 45, 45,
  /* 33607 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1758, 0, 362, 0, 0, 925, 41606, 0, 0, 0, 0, 45, 45,
  /* 33633 */ 934, 45, 45, 45, 164, 168, 174, 178, 45, 45, 45, 45, 45, 194, 45, 45, 45, 165, 45, 45, 45, 45, 45, 45, 45,
  /* 33658 */ 45, 45, 199, 45, 45, 45, 67, 67, 1010, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1060, 67, 67, 67,
  /* 33683 */ 67, 67, 67, 1052, 1053, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1063, 97, 1157, 97, 97, 97, 97, 97, 97,
  /* 33707 */ 97, 97, 97, 97, 97, 97, 1167, 97, 97, 97, 97, 97, 1379, 97, 97, 97, 0, 0, 0, 45, 1383, 45, 45, 45, 1806,
  /* 33732 */ 45, 45, 45, 45, 45, 45, 1812, 45, 45, 45, 45, 67, 67, 67, 67, 67, 1577, 67, 67, 67, 67, 67, 67, 67, 753,
  /* 33757 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 1262, 67, 67, 67, 67, 67, 67, 67, 1282, 67, 67, 67, 67, 67, 67, 67,
  /* 33782 */ 67, 67, 67, 67, 67, 67, 67, 1471, 67, 45, 1402, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 33807 */ 417, 45, 67, 1462, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 37689, 544, 97, 1517, 97, 97,
  /* 33831 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1128, 97, 97, 97, 97, 1636, 97, 97, 97, 0, 97, 97, 97, 97,
  /* 33857 */ 97, 97, 97, 97, 851, 97, 97, 97, 97, 97, 97, 97, 67, 67, 1705, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97,
  /* 33883 */ 97, 97, 97, 0, 0, 97, 97, 97, 97, 1842, 0, 0, 1779, 97, 97, 97, 1782, 97, 0, 0, 97, 97, 97, 97, 97, 97, 0,
  /* 33910 */ 0, 97, 97, 97, 1789, 97, 97, 0, 0, 0, 97, 1847, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45, 45, 45, 45, 1675,
  /* 33936 */ 45, 45, 45, 45, 45, 45, 45, 45, 737, 738, 67, 740, 67, 741, 67, 743, 67, 67, 67, 67, 67, 67, 1968, 67, 67,
  /* 33961 */ 97, 97, 97, 97, 0, 0, 0, 97, 97, 45, 67, 0, 97, 45, 67, 2062, 97, 45, 67, 0, 97, 45, 67, 67, 97, 97, 2001,
  /* 33988 */ 97, 0, 0, 2004, 97, 97, 0, 97, 97, 97, 97, 1797, 97, 97, 97, 97, 97, 45, 45, 45, 67, 261, 67, 67, 67, 67,
  /* 34014 */ 67, 0, 37139, 24853, 0, 0, 0, 0, 41098, 65820, 97, 97, 292, 97, 97, 97, 97, 311, 315, 321, 325, 97, 97,
  /* 34037 */ 97, 97, 97, 97, 1623, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1330, 97, 97, 1333, 1334, 97, 341, 97, 97,
  /* 34061 */ 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 0, 28, 28, 139621, 0, 0, 0, 363, 364, 0, 367, 41098, 369, 140,
  /* 34085 */ 45, 45, 45, 45, 1221, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 413, 45, 45, 416, 45, 376, 45, 45, 45,
  /* 34110 */ 45, 382, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1408, 45, 45, 45, 45, 45, 403, 45, 45, 45, 45, 45, 45,
  /* 34135 */ 45, 45, 45, 45, 414, 45, 45, 45, 418, 67, 67, 67, 462, 67, 67, 67, 67, 468, 67, 67, 67, 67, 67, 67, 67,
  /* 34160 */ 67, 1602, 67, 1604, 67, 67, 67, 67, 67, 67, 67, 67, 489, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 500, 67,
  /* 34185 */ 67, 67, 67, 67, 1067, 67, 67, 67, 67, 67, 1072, 67, 67, 67, 67, 67, 67, 274, 0, 37139, 24853, 0, 0, 0, 0,
  /* 34210 */ 41098, 65820, 67, 67, 504, 67, 67, 67, 67, 67, 67, 67, 510, 67, 67, 67, 517, 519, 541, 67, 37139, 37139,
  /* 34232 */ 24853, 24853, 0, 70179, 0, 0, 0, 65820, 65820, 369, 287, 554, 97, 97, 97, 559, 97, 97, 97, 97, 565, 97,
  /* 34254 */ 97, 97, 97, 97, 97, 97, 1718, 0, 97, 97, 97, 97, 97, 97, 97, 898, 97, 97, 97, 97, 97, 97, 906, 97, 97, 97,
  /* 34280 */ 97, 586, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 597, 97, 97, 97, 97, 97, 1520, 97, 97, 97, 97, 97, 97,
  /* 34305 */ 97, 97, 97, 97, 0, 45, 1656, 45, 45, 45, 97, 97, 601, 97, 97, 97, 97, 97, 97, 97, 607, 97, 97, 97, 614,
  /* 34330 */ 616, 638, 97, 18, 0, 139621, 0, 0, 0, 0, 0, 0, 364, 0, 0, 367, 41606, 369, 0, 45, 45, 45, 45, 45, 45, 45,
  /* 34356 */ 45, 45, 45, 661, 45, 45, 45, 407, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1815, 45, 67, 45,
  /* 34381 */ 667, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 678, 45, 45, 45, 421, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 34407 */ 45, 45, 976, 977, 45, 45, 45, 682, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 693, 45, 45, 697, 67, 67, 748,
  /* 34432 */ 67, 67, 67, 67, 754, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1274, 67, 67, 67, 67, 67, 67, 67, 67, 765, 67,
  /* 34457 */ 67, 67, 67, 769, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1589, 67, 67, 67, 67, 67, 67, 67, 67, 780, 67, 67,
  /* 34482 */ 784, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1777, 67, 97, 97, 97, 97, 97, 97, 846, 97, 97, 97, 97,
  /* 34507 */ 852, 97, 97, 97, 97, 97, 97, 97, 1742, 45, 45, 45, 45, 45, 45, 45, 1747, 97, 97, 97, 863, 97, 97, 97, 97,
  /* 34532 */ 867, 97, 97, 97, 97, 97, 97, 97, 308, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 12288, 1178, 925, 0, 1179,
  /* 34556 */ 0, 97, 97, 97, 878, 97, 97, 882, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 12288, 0, 925, 0, 1179, 0, 908,
  /* 34581 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0, 925, 0, 0, 0, 954, 45, 45, 45, 45, 45, 45,
  /* 34608 */ 45, 45, 45, 45, 963, 45, 45, 966, 45, 45, 157, 45, 45, 171, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 948,
  /* 34633 */ 45, 45, 45, 45, 45, 1022, 67, 67, 1026, 67, 67, 67, 1030, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1603, 1605,
  /* 34657 */ 67, 67, 67, 1608, 67, 67, 67, 1039, 67, 67, 1042, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 471, 67, 67, 67,
  /* 34682 */ 67, 67, 0, 1100, 0, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 904, 97, 97, 97, 97, 1116, 97, 97,
  /* 34708 */ 1120, 97, 97, 97, 1124, 97, 97, 97, 97, 97, 97, 562, 97, 97, 97, 571, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 34733 */ 1133, 97, 97, 1136, 97, 97, 97, 97, 97, 97, 97, 97, 915, 917, 97, 97, 97, 97, 97, 0, 97, 1170, 97, 97, 97,
  /* 34758 */ 97, 97, 97, 97, 97, 0, 0, 925, 0, 0, 0, 0, 0, 41606, 0, 0, 0, 0, 45, 45, 45, 45, 45, 45, 1993, 67, 67, 67,
  /* 34786 */ 67, 67, 67, 67, 67, 67, 67, 1275, 67, 67, 67, 1278, 67, 0, 0, 0, 45, 45, 1182, 45, 45, 45, 45, 45, 45, 45,
  /* 34812 */ 45, 45, 1189, 1204, 45, 45, 45, 1207, 45, 45, 1209, 45, 1210, 45, 45, 45, 45, 45, 45, 1546, 45, 45, 45,
  /* 34835 */ 45, 45, 45, 45, 45, 45, 689, 45, 45, 45, 45, 45, 45, 1231, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 34861 */ 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 236, 67, 67, 67, 67, 67, 67, 67, 801, 67, 67, 67, 805, 67, 67, 67,
  /* 34887 */ 67, 67, 1242, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1249, 67, 67, 67, 67, 67, 67, 507, 67, 67, 67, 67, 67,
  /* 34912 */ 67, 67, 67, 67, 67, 1300, 0, 0, 0, 0, 0, 1267, 67, 67, 1269, 67, 1270, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 34938 */ 1280, 97, 1349, 97, 1350, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1360, 97, 97, 97, 0, 1980, 97, 97, 97, 97,
  /* 34962 */ 97, 45, 45, 45, 45, 45, 45, 673, 45, 45, 45, 45, 677, 45, 45, 45, 45, 1401, 45, 45, 45, 45, 45, 45, 45,
  /* 34987 */ 45, 45, 45, 45, 45, 45, 45, 45, 953, 67, 1437, 67, 1440, 67, 67, 67, 67, 1445, 67, 67, 67, 1448, 67, 67,
  /* 35011 */ 67, 67, 67, 67, 1029, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1825, 67, 67, 67, 67, 67, 1473, 67, 67, 67,
  /* 35036 */ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1320, 0, 834, 97, 97, 97, 97, 1490, 97, 1493, 97, 97, 97, 97, 1498,
  /* 35063 */ 97, 97, 97, 1501, 97, 97, 97, 0, 97, 1638, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 916, 97, 97, 97, 97, 97,
  /* 35089 */ 97, 0, 1528, 97, 97, 97, 0, 45, 45, 45, 1535, 45, 45, 45, 45, 45, 45, 45, 1867, 67, 67, 67, 67, 67, 67,
  /* 35114 */ 67, 67, 67, 97, 97, 97, 97, 1932, 0, 0, 1555, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1567,
  /* 35139 */ 45, 45, 158, 45, 45, 172, 45, 45, 45, 183, 45, 45, 45, 45, 201, 45, 45, 67, 212, 67, 67, 67, 67, 231, 235,
  /* 35164 */ 241, 245, 67, 67, 67, 67, 67, 67, 493, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 472, 67, 67, 67, 67, 67,
  /* 35189 */ 97, 97, 97, 97, 1651, 97, 97, 97, 97, 97, 0, 45, 45, 45, 45, 45, 45, 45, 1539, 45, 45, 45, 67, 1704, 67,
  /* 35214 */ 1706, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 1841, 97, 0, 1844, 97, 97, 97,
  /* 35240 */ 97, 1716, 97, 97, 97, 0, 97, 97, 97, 97, 97, 97, 97, 590, 97, 97, 97, 97, 97, 97, 97, 97, 97, 0, 0, 0, 45,
  /* 35267 */ 45, 45, 1385, 1748, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1757, 45, 45, 159, 45, 45, 45, 45,
  /* 35292 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 415, 45, 45, 97, 97, 1780, 97, 97, 97, 0, 0, 1786, 97, 97, 97, 97, 97,
  /* 35318 */ 0, 0, 97, 97, 1730, 0, 97, 97, 97, 97, 97, 1736, 97, 1738, 67, 97, 97, 97, 97, 97, 97, 0, 1838, 97, 97,
  /* 35343 */ 97, 97, 97, 0, 0, 97, 1729, 97, 0, 97, 97, 97, 97, 97, 97, 97, 97, 1162, 97, 97, 97, 1165, 97, 97, 97, 45,
  /* 35369 */ 1950, 45, 45, 45, 45, 45, 45, 45, 45, 1958, 67, 67, 67, 1962, 67, 67, 67, 67, 67, 1246, 67, 67, 67, 67,
  /* 35393 */ 67, 67, 67, 67, 67, 67, 67, 97, 1710, 97, 97, 97, 1999, 67, 97, 97, 97, 97, 0, 2003, 97, 97, 97, 0, 97,
  /* 35418 */ 97, 2008, 2009, 45, 67, 67, 67, 67, 0, 0, 97, 97, 97, 97, 45, 2052, 67, 2053, 0, 0, 0, 0, 925, 41606, 0,
  /* 35443 */ 0, 930, 0, 45, 45, 45, 45, 45, 45, 1392, 45, 1394, 45, 45, 45, 45, 45, 45, 45, 1545, 45, 45, 45, 45, 45,
  /* 35468 */ 45, 45, 45, 45, 45, 1563, 1565, 45, 45, 45, 1568, 0, 97, 2055, 45, 67, 0, 97, 45, 67, 0, 97, 45, 67,
  /* 35492 */ 28672, 97, 45, 45, 160, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 679, 45, 45, 67, 67, 266, 67,
  /* 35517 */ 67, 67, 67, 0, 37139, 24853, 0, 0, 0, 0, 41098, 65820, 97, 346, 97, 97, 97, 97, 0, 53264, 0, 18, 18, 24,
  /* 35541 */ 24, 0, 28, 28, 139621, 0, 0, 362, 0, 364, 0, 367, 41098, 369, 140, 371, 45, 45, 45, 379, 45, 45, 45, 388,
  /* 35565 */ 45, 45, 45, 45, 45, 45, 45, 45, 1663, 45, 45, 45, 45, 45, 45, 45, 45, 45, 449, 45, 45, 45, 45, 45, 67, 67,
  /* 35591 */ 542, 37139, 37139, 24853, 24853, 0, 70179, 0, 0, 0, 65820, 65820, 369, 287, 97, 97, 97, 97, 97, 1622, 97,
  /* 35612 */ 97, 97, 97, 97, 97, 97, 1629, 97, 97, 0, 1794, 1795, 97, 97, 97, 97, 97, 97, 97, 97, 45, 45, 45, 45, 45,
  /* 35637 */ 45, 1745, 45, 45, 97, 639, 18, 0, 139621, 0, 0, 0, 0, 0, 0, 364, 0, 0, 367, 41606, 45, 731, 45, 45, 45,
  /* 35662 */ 45, 45, 45, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 251, 67, 67, 67, 67, 67, 798, 67, 67, 67, 67,
  /* 35688 */ 67, 67, 67, 67, 67, 67, 67, 67, 1073, 67, 67, 67, 860, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 35714 */ 97, 873, 0, 0, 1101, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 921, 97, 0, 67, 67, 67, 67, 1245,
  /* 35740 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1250, 67, 67, 1253, 0, 0, 1312, 0, 0, 0, 1318, 0, 0, 0, 0,
  /* 35767 */ 0, 0, 97, 97, 97, 97, 1106, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1149, 97, 97, 97, 97, 97, 1155, 97, 97,
  /* 35792 */ 1325, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1141, 97, 97, 67, 67, 1439, 67, 1441, 67, 67,
  /* 35816 */ 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1264, 67, 67, 67, 97, 97, 1492, 97, 1494, 97, 97, 97, 97, 97, 97,
  /* 35841 */ 97, 97, 97, 97, 97, 1331, 97, 97, 97, 97, 67, 67, 67, 2037, 67, 97, 0, 0, 97, 97, 97, 2043, 97, 45, 45,
  /* 35866 */ 45, 442, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 67, 67, 67, 67, 67, 67, 232, 67, 67, 67, 67, 67, 67,
  /* 35892 */ 67, 67, 1823, 67, 67, 67, 67, 67, 67, 67, 67, 97, 97, 97, 97, 1975, 0, 0, 97, 874, 97, 97, 97, 97, 97, 97,
  /* 35918 */ 97, 97, 97, 97, 97, 97, 97, 97, 97, 1142, 97, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630,
  /* 35939 */ 114730, 106539, 65, 86, 117, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539,
  /* 35956 */ 63, 84, 115, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 61, 82, 113,
  /* 35974 */ 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 59, 80, 111, 53264, 18, 49172,
  /* 35992 */ 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 57, 78, 109, 53264, 18, 49172, 57366, 24, 8192,
  /* 36010 */ 28, 102432, 37, 110630, 114730, 106539, 55, 76, 107, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37,
  /* 36028 */ 110630, 114730, 106539, 53, 74, 105, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730,
  /* 36045 */ 106539, 51, 72, 103, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 49, 70,
  /* 36063 */ 101, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 47, 68, 99, 53264, 18,
  /* 36081 */ 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 45, 67, 97, 53264, 18, 49172, 57366, 24,
  /* 36099 */ 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 213085, 53264, 18, 49172, 57366, 24, 8192, 28, 102432,
  /* 36117 */ 0, 0, 0, 44, 0, 0, 32863, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 0, 41, 41, 41, 0, 0, 1138688,
  /* 36139 */ 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 0, 53264, 18, 49172,
  /* 36157 */ 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 89, 53264, 18, 18, 49172, 0, 57366, 0, 24,
  /* 36177 */ 24, 24, 0, 127, 127, 127, 127, 102432, 67, 262, 67, 67, 67, 67, 67, 0, 37139, 24853, 0, 0, 0, 0, 41098,
  /* 36200 */ 65820, 342, 97, 97, 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 0, 28, 28, 139621, 0, 360, 0, 0, 364, 0, 367,
  /* 36225 */ 41098, 369, 140, 45, 45, 45, 45, 717, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 412, 45, 45, 45, 45, 45,
  /* 36250 */ 67, 1009, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 1292, 67, 67, 1294, 67, 67, 67, 67, 67, 67,
  /* 36275 */ 67, 67, 67, 67, 0, 0, 0, 0, 0, 0, 97, 97, 97, 1615, 97, 97, 97, 53264, 18, 49172, 57366, 24, 8192, 28,
  /* 36299 */ 102432, 37, 110630, 114730, 106539, 66, 87, 118, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37,
  /* 36316 */ 110630, 114730, 106539, 64, 85, 116, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730,
  /* 36333 */ 106539, 62, 83, 114, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 60, 81,
  /* 36351 */ 112, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 58, 79, 110, 53264, 18,
  /* 36369 */ 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 56, 77, 108, 53264, 18, 49172, 57366, 24,
  /* 36387 */ 8192, 28, 102432, 37, 110630, 114730, 106539, 54, 75, 106, 53264, 18, 49172, 57366, 24, 8192, 28, 102432,
  /* 36405 */ 37, 110630, 114730, 106539, 52, 73, 104, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630,
  /* 36422 */ 114730, 106539, 50, 71, 102, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539,
  /* 36439 */ 48, 69, 100, 53264, 18, 49172, 57366, 24, 8192, 28, 102432, 37, 110630, 114730, 106539, 46, 67, 98, 53264,
  /* 36458 */ 18, 49172, 57366, 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 233472, 53264, 18, 49172, 57366,
  /* 36476 */ 24, 8192, 28, 102432, 0, 110630, 114730, 106539, 0, 0, 69724, 53264, 18, 18, 49172, 0, 57366, 262144, 24,
  /* 36495 */ 24, 24, 0, 28, 28, 28, 28, 102432, 45, 45, 161, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 710,
  /* 36520 */ 45, 45, 28, 139621, 359, 0, 0, 0, 364, 0, 367, 41098, 369, 140, 45, 45, 45, 45, 1389, 45, 45, 45, 45, 45,
  /* 36544 */ 45, 45, 45, 45, 45, 45, 949, 45, 45, 45, 45, 67, 503, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67,
  /* 36570 */ 67, 1449, 67, 67, 97, 600, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1154, 97, 0, 0, 0, 0,
  /* 36596 */ 925, 41606, 927, 0, 0, 0, 45, 45, 45, 45, 45, 45, 1866, 67, 67, 67, 67, 67, 67, 67, 67, 67, 67, 772, 67,
  /* 36621 */ 67, 67, 67, 67, 45, 45, 969, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 951, 45, 45, 45, 45,
  /* 36646 */ 1192, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1202, 45, 45, 0, 0, 0, 1314, 0, 0, 0, 0, 0, 0,
  /* 36673 */ 0, 0, 0, 97, 97, 97, 97, 97, 97, 97, 1488, 67, 67, 267, 67, 67, 67, 67, 0, 37139, 24853, 0, 0, 0, 0,
  /* 36698 */ 41098, 65820, 97, 347, 97, 97, 97, 97, 0, 53264, 0, 18, 18, 24, 24, 0, 28, 28, 139621, 0, 361, 0, 0, 364,
  /* 36722 */ 0, 367, 41098, 369, 140, 45, 45, 45, 45, 734, 45, 45, 45, 67, 67, 67, 67, 67, 742, 67, 67, 45, 45, 668,
  /* 36746 */ 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 1214, 45, 45, 1130, 97, 97, 97, 97, 97, 97, 97, 97,
  /* 36771 */ 97, 97, 97, 97, 97, 97, 97, 1361, 97, 45, 45, 1671, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 36796 */ 1552, 45, 45, 0, 0, 0, 0, 2220032, 0, 0, 1130496, 0, 0, 0, 0, 2170880, 2171020, 2170880, 2170880, 18, 0,
  /* 36817 */ 0, 131072, 0, 0, 0, 90112, 0, 2220032, 0, 0, 0, 0, 0, 0, 0, 0, 97, 97, 97, 1485, 97, 97, 97, 97, 0, 45,
  /* 36843 */ 45, 45, 45, 45, 1537, 45, 45, 45, 45, 45, 1390, 45, 1393, 45, 45, 45, 45, 1398, 45, 45, 45, 2170880,
  /* 36865 */ 2171167, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880,
  /* 36876 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2576384, 2215936, 3117056, 2215936, 2215936,
  /* 36887 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 0, 0, 0, 0, 0,
  /* 36902 */ 0, 2174976, 0, 0, 0, 0, 0, 0, 2183168, 0, 0, 0, 0, 2170880, 2170880, 2170880, 2400256, 2170880, 2170880,
  /* 36921 */ 2170880, 2170880, 2721252, 2744320, 2170880, 2170880, 2170880, 2834432, 2840040, 2170880, 2908160,
  /* 36932 */ 2170880, 2170880, 2936832, 2170880, 2170880, 2985984, 2170880, 2994176, 2170880, 2170880, 3014656,
  /* 36943 */ 2170880, 3059712, 3076096, 3088384, 2170880, 2170880, 2170880, 2170880, 0, 0, 0, 0, 2220032, 0, 0, 0,
  /* 36959 */ 1142784, 0, 0, 0, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 3215360, 2215936,
  /* 36972 */ 2215936, 2215936, 2215936, 2215936, 2437120, 2215936, 2215936, 2215936, 3117056, 2215936, 2215936,
  /* 36983 */ 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 2215936, 0, 543, 0, 545,
  /* 36997 */ 0, 0, 2183168, 0, 0, 831, 0, 2170880, 2170880, 2170880, 2400256, 2170880, 2170880, 2170880, 2170880,
  /* 37012 */ 3031040, 2170880, 3055616, 2170880, 2170880, 2170880, 2170880, 3092480, 2170880, 2170880, 3125248,
  /* 37023 */ 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 2170880, 3198976, 2170880, 0, 0,
  /* 37036 */ 0, 0, 0, 0, 67, 67, 37139, 37139, 24853, 24853, 0, 0, 0, 0, 0, 65820, 65820, 0, 287, 97, 97, 97, 97, 97,
  /* 37060 */ 1783, 0, 0, 97, 97, 97, 97, 97, 97, 0, 0, 97, 97, 97, 97, 97, 97, 1791, 0, 0, 546, 70179, 0, 0, 0, 0, 552,
  /* 37087 */ 0, 97, 97, 97, 97, 97, 97, 97, 604, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 1150, 97, 97, 97, 97, 97,
  /* 37112 */ 147456, 147456, 147456, 147456, 147456, 147456, 147456, 147456, 147456, 147456, 147456, 147456, 0, 0,
  /* 37126 */ 147456, 0, 0, 0, 0, 925, 41606, 0, 928, 0, 0, 45, 45, 45, 45, 45, 45, 998, 45, 45, 45, 45, 45, 45, 45, 45,
  /* 37152 */ 45, 1562, 45, 1564, 45, 45, 45, 45, 0, 2158592, 2158592, 0, 0, 0, 0, 2232320, 2232320, 2232320, 0,
  /* 37171 */ 2240512, 2240512, 2240512, 2240512, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2170880, 2170880, 2170880, 2416640
];

JSONiqTokenizer.EXPECTED =
[
  /*    0 */ 291, 300, 304, 341, 315, 309, 305, 295, 319, 323, 327, 329, 296, 333, 337, 339, 342, 346, 350, 294, 356,
  /*   21 */ 360, 312, 367, 352, 371, 363, 375, 379, 383, 387, 391, 395, 726, 399, 405, 518, 684, 405, 405, 405, 405,
  /*   42 */ 808, 405, 405, 405, 512, 405, 405, 405, 431, 405, 405, 406, 405, 405, 404, 405, 405, 405, 405, 405, 405,
  /*   63 */ 405, 908, 631, 410, 415, 405, 414, 419, 608, 405, 429, 602, 405, 435, 443, 405, 441, 641, 478, 405, 447,
  /*   84 */ 451, 450, 456, 643, 461, 460, 762, 679, 465, 469, 741, 473, 477, 482, 486, 492, 932, 931, 523, 498, 504,
  /*  105 */ 720, 405, 510, 596, 405, 516, 941, 580, 522, 929, 527, 590, 589, 897, 939, 534, 538, 547, 551, 555, 559,
  /*  126 */ 563, 567, 571, 969, 575, 708, 690, 689, 579, 584, 634, 405, 594, 731, 405, 600, 882, 405, 606, 895, 786,
  /*  147 */ 452, 612, 405, 615, 620, 876, 624, 628, 638, 647, 651, 655, 659, 663, 667, 676, 683, 688, 695, 694, 791,
  /*  168 */ 405, 699, 437, 405, 706, 714, 405, 712, 825, 870, 405, 718, 724, 769, 768, 823, 730, 735, 745, 751, 422,
  /*  189 */ 755, 759, 425, 766, 902, 810, 587, 775, 888, 887, 405, 773, 992, 405, 779, 962, 405, 785, 781, 986, 790,
  /*  210 */ 795, 797, 506, 500, 499, 801, 805, 814, 820, 829, 833, 837, 841, 845, 849, 853, 857, 861, 616, 865, 869,
  /*  231 */ 868, 488, 405, 874, 816, 405, 880, 738, 405, 886, 892, 543, 405, 901, 906, 913, 912, 918, 494, 541, 922,
  /*  252 */ 926, 936, 945, 949, 953, 957, 530, 966, 973, 960, 702, 701, 405, 979, 981, 405, 985, 747, 405, 990, 998,
  /*  273 */ 914, 405, 996, 1004, 672, 975, 974, 1014, 1002, 1008, 670, 1012, 405, 405, 405, 405, 405, 401, 1018, 1022,
  /*  293 */ 1026, 1106, 1071, 1111, 1111, 1111, 1082, 1145, 1030, 1101, 1034, 1038, 1106, 1106, 1106, 1106, 1046, 1206,
  /*  311 */ 1052, 1106, 1072, 1111, 1111, 1042, 1134, 1065, 1111, 1112, 1056, 1160, 1207, 1062, 1204, 1208, 1069, 1106,
  /*  329 */ 1106, 1106, 1076, 1111, 1207, 1161, 1122, 1205, 1064, 1094, 1106, 1106, 1107, 1111, 1111, 1111, 1078, 1086,
  /*  347 */ 1207, 1092, 1098, 1046, 1058, 1106, 1106, 1110, 1111, 1111, 1116, 1120, 1161, 1126, 1202, 1104, 1106, 1145,
  /*  365 */ 1146, 1129, 1138, 1088, 1151, 1048, 1157, 1153, 1132, 1141, 1165, 1107, 1111, 1172, 1179, 1109, 1183, 1175,
  /*  383 */ 1143, 1147, 1187, 1108, 1191, 1195, 1144, 1199, 1168, 1212, 1216, 1220, 1224, 1228, 1232, 1236, 1557, 1247,
  /*  401 */ 1241, 1241, 1038, 1434, 1241, 1241, 1241, 1241, 1254, 1275, 1617, 1241, 1280, 1287, 1241, 1241, 1241, 1287,
  /*  419 */ 1241, 2114, 1291, 1241, 1243, 1241, 2049, 1824, 2094, 2095, 1520, 1309, 1241, 1241, 1302, 1241, 1321, 1311,
  /*  437 */ 1241, 1241, 1313, 1778, 1325, 1336, 1241, 1241, 1325, 1330, 1353, 1241, 1241, 1695, 1354, 1241, 1241, 1241,
  /*  455 */ 1294, 1686, 1331, 1241, 1696, 1368, 1241, 1338, 1370, 1241, 1392, 1399, 1364, 2017, 1406, 2016, 1405, 1716,
  /*  473 */ 1406, 1407, 1422, 1417, 1421, 1241, 1241, 1241, 1349, 1426, 1241, 1774, 1756, 1241, 1773, 1241, 1241, 1345,
  /*  491 */ 1964, 1812, 1432, 1241, 1241, 1345, 1993, 1459, 1241, 1241, 1241, 1395, 1848, 1767, 1465, 1241, 1241, 1394,
  /*  509 */ 1847, 1242, 1477, 1241, 1241, 1428, 1241, 1445, 1492, 1241, 1241, 1438, 1241, 1499, 1241, 1241, 1241, 1455,
  /*  527 */ 1241, 1818, 1448, 1241, 1250, 1241, 2026, 1623, 1449, 1241, 1612, 1616, 1241, 1614, 1241, 1257, 1241, 1241,
  /*  545 */ 1985, 1292, 1586, 1512, 1241, 1517, 2050, 1526, 1674, 1519, 1524, 1647, 2051, 1532, 1537, 1551, 1544, 1550,
  /*  563 */ 1555, 1561, 1571, 1578, 1584, 1590, 1591, 1653, 1595, 1602, 1606, 1610, 1634, 1628, 1640, 1633, 1645, 1241,
  /*  581 */ 1241, 1241, 1469, 1241, 1970, 1651, 1241, 1270, 1241, 1241, 1819, 1449, 1241, 1293, 1664, 1241, 1241, 1481,
  /*  599 */ 1485, 1574, 1672, 1241, 1241, 1513, 1317, 1487, 1684, 1241, 1241, 1533, 1299, 1694, 1241, 1241, 1295, 1241,
  /*  617 */ 1241, 1241, 1546, 1700, 1241, 1241, 1707, 1241, 1713, 1241, 1849, 1715, 1241, 1720, 1241, 1276, 1267, 1241,
  /*  635 */ 1241, 2107, 1657, 1864, 1241, 1881, 1241, 1326, 1292, 1241, 1685, 1358, 1724, 1338, 1241, 1363, 1362, 1342,
  /*  653 */ 1340, 1361, 1339, 1833, 1372, 1360, 1833, 1833, 1342, 1343, 1835, 1341, 1731, 1738, 1344, 1241, 1745, 1241,
  /*  671 */ 1379, 1241, 1241, 2092, 1241, 1388, 1761, 1754, 1241, 1386, 1241, 1400, 1760, 1241, 1241, 1241, 1598, 1734,
  /*  689 */ 1241, 1241, 1241, 1635, 1645, 1241, 1780, 1766, 1241, 1241, 1332, 1771, 1241, 1241, 1629, 2079, 1241, 1242,
  /*  707 */ 1784, 1241, 1241, 1680, 1639, 2063, 1790, 1241, 1241, 1741, 1241, 1241, 1800, 1241, 1241, 1762, 1473, 1241,
  /*  725 */ 1806, 1241, 1241, 1786, 1240, 1709, 1241, 1241, 1241, 1668, 1811, 1241, 1940, 1241, 1401, 1974, 1241, 1408,
  /*  743 */ 1413, 1382, 1241, 1816, 1241, 1241, 1802, 2086, 1811, 1241, 1817, 1945, 1823, 2095, 2095, 2047, 2094, 2046,
  /*  761 */ 2080, 1241, 1409, 1312, 1376, 2096, 2048, 1241, 1241, 1807, 1241, 1241, 1241, 2035, 1241, 1241, 1828, 1241,
  /*  779 */ 2057, 2061, 1241, 1241, 1843, 1241, 2059, 1241, 1241, 1241, 1690, 1847, 1241, 1241, 1241, 1703, 2102, 1848,
  /*  797 */ 1241, 1241, 1853, 1292, 1848, 1241, 2016, 1857, 1241, 2002, 1868, 1241, 1436, 1241, 1241, 1271, 1305, 1241,
  /*  815 */ 1874, 1241, 1241, 1884, 2037, 1892, 1241, 1890, 1241, 1461, 1241, 1241, 1795, 1241, 1241, 1891, 1241, 1878,
  /*  833 */ 1241, 1888, 1241, 1888, 1905, 1896, 2087, 1912, 1903, 1241, 1911, 1906, 1916, 1905, 2027, 1863, 1925, 2088,
  /*  851 */ 1859, 1861, 1922, 1927, 1931, 1935, 1494, 1241, 1241, 1918, 1907, 1939, 1917, 1944, 1949, 1241, 1241, 1451,
  /*  869 */ 1955, 1241, 1241, 1241, 1796, 1727, 2061, 1241, 1241, 1899, 1241, 1660, 1968, 1241, 1241, 1951, 1678, 1978,
  /*  887 */ 1241, 1241, 1241, 1839, 1241, 1241, 1984, 1982, 1241, 1488, 1241, 1241, 1624, 1450, 1989, 1241, 1241, 1241,
  /*  905 */ 1870, 1995, 1292, 1241, 1241, 1958, 1261, 1241, 1996, 1241, 1241, 1241, 2039, 2008, 1241, 1241, 1750, 2000,
  /*  923 */ 1241, 1256, 2001, 1960, 1241, 1564, 1241, 1504, 1241, 1241, 1442, 1241, 1241, 1564, 1528, 1263, 1241, 1508,
  /*  941 */ 1241, 1241, 1468, 1498, 2006, 1540, 2015, 1539, 2014, 1748, 2013, 1539, 1831, 2014, 2012, 1500, 1567, 2022,
  /*  959 */ 2021, 1241, 1580, 1241, 1241, 2033, 2037, 1791, 2045, 2031, 1241, 1621, 1241, 1641, 2044, 1241, 1241, 1241,
  /*  977 */ 2093, 1241, 1241, 2055, 1241, 1241, 2067, 1241, 1283, 1241, 1241, 1241, 2101, 2071, 1241, 1241, 1241, 2073,
  /*  995 */ 1848, 2040, 1241, 1241, 1241, 2077, 1241, 1241, 2106, 1241, 1241, 2084, 1241, 2111, 1241, 1241, 1381, 1380,
  /* 1013 */ 1241, 1241, 1241, 2100, 1241, 2129, 2118, 2122, 2126, 2197, 2133, 3010, 2825, 2145, 2698, 2156, 2226, 2160,
  /* 1031 */ 2161, 2165, 2174, 2293, 2194, 2630, 2201, 2203, 2152, 3019, 2226, 2263, 2209, 2213, 2218, 2269, 2292, 2269,
  /* 1049 */ 2269, 2184, 2226, 2238, 2148, 2151, 3017, 2245, 2214, 2269, 2269, 2185, 2226, 2292, 2269, 2291, 2269, 2269,
  /* 1067 */ 2269, 2292, 2205, 3019, 2226, 2226, 2160, 2160, 2160, 2261, 2160, 2160, 2160, 2262, 2276, 2160, 2160, 2277,
  /* 1085 */ 2216, 2283, 2216, 2269, 2269, 2268, 2269, 2267, 2269, 2269, 2269, 2271, 2568, 2292, 2269, 2293, 2269, 2182,
  /* 1103 */ 2190, 2269, 2186, 2226, 2226, 2226, 2226, 2227, 2160, 2160, 2160, 2160, 2263, 2160, 2275, 2277, 2282, 2215,
  /* 1121 */ 2217, 2269, 2269, 2291, 2269, 2269, 2293, 2291, 2269, 2220, 2269, 2295, 2294, 2269, 2269, 2305, 2233, 2262,
  /* 1139 */ 2278, 2218, 2269, 2234, 2226, 2226, 2228, 2160, 2160, 2160, 2289, 2220, 2294, 2294, 2269, 2269, 2304, 2269,
  /* 1157 */ 2160, 2160, 2287, 2269, 2269, 2305, 2269, 2269, 2312, 2269, 2269, 2225, 2226, 2160, 2287, 2289, 2219, 2304,
  /* 1175 */ 2295, 2314, 2234, 2226, 2314, 2269, 2226, 2226, 2160, 2288, 2219, 2222, 2304, 2296, 2269, 2224, 2160, 2160,
  /* 1193 */ 2269, 2302, 2294, 2314, 2224, 2226, 2288, 2220, 2294, 2269, 2290, 2269, 2269, 2293, 2269, 2269, 2269, 2269,
  /* 1211 */ 2270, 2221, 2313, 2225, 2227, 2160, 2300, 2269, 2225, 2261, 2309, 2234, 2229, 2223, 2318, 2318, 2318, 2328,
  /* 1229 */ 2336, 2340, 2344, 2350, 2637, 2712, 2358, 2362, 2372, 2135, 2378, 2398, 2135, 2135, 2135, 2135, 2136, 2417,
  /* 1247 */ 2241, 2135, 2378, 2135, 2135, 2980, 2984, 2135, 3006, 2135, 2135, 2135, 2945, 2931, 2425, 2400, 2135, 2135,
  /* 1265 */ 2135, 2954, 2135, 2481, 2433, 2135, 2135, 2988, 2824, 2135, 2135, 2482, 2434, 2135, 2135, 2440, 2445, 2452,
  /* 1283 */ 2135, 2135, 2998, 3002, 2961, 2441, 2446, 2453, 2463, 2974, 2135, 2135, 2135, 2140, 2642, 2709, 2459, 2470,
  /* 1301 */ 2465, 2135, 2135, 3005, 2135, 2135, 2987, 2823, 2458, 2469, 2464, 2975, 2135, 2135, 2135, 2353, 2488, 2447,
  /* 1319 */ 2324, 2974, 2135, 2409, 2459, 2448, 2135, 2961, 2487, 2446, 2476, 2323, 2973, 2135, 2135, 2135, 2354, 2476,
  /* 1337 */ 2974, 2135, 2135, 2135, 2957, 2135, 2135, 2960, 2135, 2135, 2135, 2363, 2409, 2459, 2474, 2465, 2487, 2571,
  /* 1355 */ 2973, 2135, 2135, 2168, 2973, 2135, 2135, 2135, 2959, 2135, 2135, 2135, 2506, 2135, 2957, 2488, 2170, 2135,
  /* 1373 */ 2135, 2135, 2960, 2135, 2818, 2493, 2135, 2135, 3033, 2135, 2135, 2135, 2934, 2819, 2494, 2135, 2135, 2135,
  /* 1391 */ 2976, 2780, 2499, 2135, 2135, 2135, 3000, 2968, 2135, 2935, 2135, 2135, 2135, 2364, 2507, 2135, 2135, 2934,
  /* 1409 */ 2135, 2135, 2780, 2492, 2507, 2135, 2135, 2506, 2780, 2135, 2135, 2782, 2780, 2135, 2782, 2135, 2783, 2374,
  /* 1427 */ 2514, 2135, 2135, 2135, 3007, 2530, 2974, 2135, 2135, 2135, 3008, 2135, 2135, 2134, 2135, 2526, 2531, 2975,
  /* 1445 */ 2135, 2135, 3042, 2581, 2575, 2956, 2135, 2135, 2135, 2394, 2135, 2508, 2535, 2840, 2844, 2495, 2135, 2135,
  /* 1463 */ 2136, 2684, 2537, 2842, 2846, 2135, 2136, 2561, 2581, 2551, 2536, 2841, 2845, 2975, 3043, 2582, 2843, 2555,
  /* 1481 */ 2135, 3040, 3044, 2538, 2844, 2975, 2135, 2135, 2253, 2644, 2672, 2542, 2554, 2135, 2135, 2346, 2873, 2551,
  /* 1499 */ 2555, 2135, 2135, 2135, 2381, 2559, 2565, 2538, 2553, 2135, 2560, 2914, 2576, 2590, 2135, 2135, 2135, 2408,
  /* 1517 */ 2136, 2596, 2624, 2135, 2135, 2135, 2409, 2135, 2618, 2597, 3008, 2135, 2135, 2380, 2956, 2601, 2135, 2135,
  /* 1535 */ 2135, 2410, 2620, 2624, 2135, 2136, 2383, 2135, 2135, 2783, 2623, 2135, 2135, 2393, 2888, 2136, 2621, 3008,
  /* 1553 */ 2135, 2618, 2618, 2622, 2135, 2135, 2405, 2414, 2619, 2384, 2624, 2135, 2136, 2950, 2135, 2138, 2135, 2139,
  /* 1571 */ 2135, 2604, 2623, 2135, 2140, 2878, 2665, 2957, 2622, 2135, 2135, 2428, 2762, 2606, 2612, 2135, 2135, 2501,
  /* 1589 */ 2586, 2604, 3038, 2135, 2604, 3036, 2387, 2958, 2386, 2135, 2141, 2135, 2421, 2387, 2385, 2135, 2385, 2384,
  /* 1607 */ 2384, 2135, 2386, 2628, 2384, 2135, 2135, 2501, 2596, 2591, 2135, 2135, 2135, 2400, 2135, 2634, 2135, 2135,
  /* 1625 */ 2559, 2580, 2575, 2648, 2135, 2135, 2135, 2429, 2649, 2135, 2135, 2135, 2435, 2654, 2658, 2135, 2135, 2135,
  /* 1643 */ 2436, 2649, 2178, 2659, 2135, 2135, 2595, 2601, 2669, 2677, 2135, 2135, 2616, 2957, 2879, 2665, 2691, 2135,
  /* 1661 */ 2363, 2367, 2900, 2878, 2664, 2690, 2975, 2877, 2643, 2670, 2974, 2671, 2975, 2135, 2135, 2619, 2608, 2669,
  /* 1679 */ 2673, 2135, 2135, 2653, 2177, 2672, 2135, 2135, 2135, 2486, 2168, 2251, 2255, 2695, 2974, 2709, 2135, 2135,
  /* 1697 */ 2135, 2487, 2169, 2399, 2716, 2975, 2135, 2363, 2770, 2776, 2640, 2717, 2135, 2135, 2729, 2135, 2135, 2641,
  /* 1715 */ 2718, 2135, 2135, 2135, 2505, 2135, 2640, 2257, 2974, 2135, 2727, 2975, 2135, 2365, 2332, 2895, 2957, 2135,
  /* 1733 */ 2959, 2135, 2365, 2749, 2754, 2959, 2958, 2958, 2135, 2380, 2793, 2799, 2135, 2735, 2738, 2135, 2381, 2135,
  /* 1751 */ 2135, 2940, 2974, 2135, 2744, 2135, 2135, 2739, 2519, 2976, 2745, 2135, 2135, 2135, 2509, 2755, 2135, 2135,
  /* 1769 */ 2135, 2510, 2772, 2778, 2135, 2135, 2740, 2520, 2135, 2771, 2777, 2135, 2135, 2759, 2750, 2792, 2798, 2135,
  /* 1787 */ 2135, 2781, 2392, 2779, 2135, 2135, 2135, 2521, 2135, 2679, 2248, 2135, 2135, 2681, 2480, 2135, 2135, 2786,
  /* 1805 */ 3000, 2135, 2679, 2683, 2135, 2135, 2416, 2135, 2135, 2135, 2525, 2135, 2730, 2135, 2135, 2135, 2560, 2581,
  /* 1823 */ 2135, 2805, 2135, 2135, 2804, 2962, 2832, 2974, 2135, 2382, 2135, 2135, 2958, 2135, 2135, 2960, 2135, 2829,
  /* 1841 */ 2833, 2975, 2961, 2965, 2969, 2973, 2968, 2972, 2135, 2135, 2135, 2641, 2135, 2515, 2966, 2970, 2851, 2478,
  /* 1859 */ 2135, 2135, 2808, 2135, 2809, 2135, 2135, 2135, 2722, 2852, 2479, 2135, 2135, 2815, 2135, 2135, 2766, 2853,
  /* 1877 */ 2480, 2135, 2857, 2479, 2135, 2388, 2723, 2135, 2364, 2331, 2894, 2858, 2480, 2135, 2135, 2850, 2478, 2135,
  /* 1895 */ 2135, 2135, 2806, 2864, 2135, 2399, 2256, 2974, 2865, 2135, 2135, 2862, 2135, 2135, 2135, 2685, 2807, 2865,
  /* 1913 */ 2135, 2135, 2807, 2863, 2135, 2135, 2135, 2686, 2884, 2807, 2135, 2809, 2807, 2135, 2135, 2807, 2806, 2705,
  /* 1931 */ 2810, 2808, 2700, 2869, 2702, 2702, 2702, 2704, 2883, 2135, 2135, 2135, 2730, 2884, 2135, 2135, 2135, 2731,
  /* 1949 */ 2321, 2546, 2135, 2135, 2876, 2255, 2889, 2322, 2547, 2135, 2401, 2135, 2135, 2135, 2949, 2367, 2893, 2544,
  /* 1967 */ 2973, 2906, 2973, 2135, 2135, 2877, 2663, 2368, 2901, 2907, 2974, 2366, 2899, 2905, 2972, 2920, 2974, 2135,
  /* 1985 */ 2135, 2911, 2900, 2920, 2363, 2913, 2918, 2465, 2941, 2975, 2135, 2135, 2924, 2928, 2974, 2945, 2931, 2135,
  /* 2003 */ 2135, 2135, 2765, 2136, 2955, 2135, 2135, 2939, 2931, 2380, 2135, 2135, 2380, 2135, 2135, 2135, 2780, 2507,
  /* 2021 */ 2137, 2135, 2137, 2135, 2139, 2135, 2806, 2810, 2135, 2135, 2135, 2992, 2135, 2135, 2962, 2966, 2970, 2974,
  /* 2039 */ 2135, 2135, 2787, 3014, 2135, 2521, 2993, 2135, 2135, 2135, 2803, 2135, 2135, 2135, 2618, 2607, 2997, 3001,
  /* 2057 */ 2135, 2135, 2963, 2967, 2971, 2975, 2135, 2135, 2791, 2797, 2135, 3009, 2999, 3003, 2787, 3001, 2135, 2135,
  /* 2075 */ 2964, 2968, 2785, 2999, 3003, 2135, 2135, 2135, 2804, 2785, 2999, 3004, 2135, 2135, 2135, 2807, 2135, 2135,
  /* 2093 */ 3023, 2135, 2135, 2135, 2811, 2135, 2135, 3027, 2135, 2135, 2135, 2837, 2968, 3028, 2135, 2135, 2135, 2875,
  /* 2111 */ 2135, 2784, 3029, 2135, 2408, 2457, 2446, 0, 14, 0, -2120220672, 1610612736, -2074083328, -2002780160,
  /* 2125 */ -2111830528, 1073872896, 1342177280, 1075807216, 4096, 16384, 2048, 8192, 0, 8192, 0, 0, 0, 0, 1, 0, 0, 0,
  /* 2143 */ 2, 0, -2145386496, 8388608, 1073741824, 0, 0x80000000, 0x80000000, 2097152, 2097152, 2097152, 536870912, 0,
  /* 2156 */ 0, 134217728, 33554432, 1536, 268435456, 268435456, 268435456, 268435456, 128, 256, 32, 0, 65536, 131072,
  /* 2170 */ 524288, 16777216, 268435456, 0x80000000, 1572864, 1835008, 640, 32768, 65536, 262144, 1048576, 2097152,
  /* 2182 */ 196608, 196800, 196608, 196608, 0, 131072, 131072, 131072, 196608, 196624, 196608, 196624, 196608, 196608,
  /* 2196 */ 128, 4096, 16384, 16384, 2048, 0, 4, 0, 0, 0x80000000, 2097152, 0, 1024, 32, 32, 0, 65536, 1572864,
  /* 2214 */ 1048576, 32768, 32768, 32768, 32768, 196608, 196608, 196608, 64, 64, 196608, 196608, 131072, 131072,
  /* 2228 */ 131072, 131072, 268435456, 268435456, 64, 196736, 196608, 196608, 196608, 131072, 196608, 196608, 16384, 4,
  /* 2242 */ 4, 4, 2, 32, 32, 65536, 1048576, 12582912, 1073741824, 0, 0, 2, 8, 16, 96, 2048, 32768, 0, 0, 131072,
  /* 2262 */ 268435456, 268435456, 268435456, 256, 256, 196608, 196672, 196608, 196608, 196608, 196608, 4, 0, 256, 256,
  /* 2277 */ 256, 256, 32, 32, 32768, 32, 32, 32, 32, 32768, 268435456, 268435456, 268435456, 196608, 196608, 196608,
  /* 2293 */ 196624, 196608, 196608, 196608, 16, 16, 16, 268435456, 196608, 64, 64, 64, 196608, 196608, 196608, 196672,
  /* 2309 */ 268435456, 64, 64, 196608, 196608, 16, 196608, 196608, 196608, 268435456, 64, 196608, 131072, 262144,
  /* 2323 */ 4194304, 25165824, 33554432, 134217728, 268435456, 268435456, 196608, 262152, 8, 256, 512, 3072, 16384,
  /* 2336 */ 200, -1073741816, 8392713, 40, 8392718, 520, 807404072, 40, 520, 100663304, 0, 0, -540651761, -540651761,
  /* 2350 */ 257589048, 0, 262144, 0, 0, 3, 8, 256, 0, 4, 6, 4100, 8388612, 0, 0, 0, 3, 4, 8, 256, 512, 1024, 0,
  /* 2373 */ 2097152, 0, 0, -537854471, -537854471, 0, 100663296, 0, 0, 1, 2, 0, 0, 0, 16384, 0, 0, 0, 96, 14336, 0, 0,
  /* 2395 */ 0, 7, 8, 234881024, 0, 0, 0, 8, 0, 0, 0, 0, 262144, 0, 0, 16, 64, 384, 512, 0, 1, 1, 0, 12582912, 0, 0, 0,
  /* 2422 */ 0, 33554432, 67108864, -606084144, -606084144, -606084138, 0, 0, 28, 32, 768, 1966080, -608174080, 0, 0, 0,
  /* 2438 */ 14, 35056, 16, 64, 896, 24576, 98304, 98304, 131072, 262144, 524288, 1048576, 4194304, 25165824, 1048576,
  /* 2453 */ 62914560, 134217728, -805306368, 0, 384, 512, 16384, 65536, 131072, 262144, 29360128, 33554432, 134217728,
  /* 2466 */ 268435456, 1073741824, 0x80000000, 262144, 524288, 1048576, 29360128, 33554432, 524288, 1048576, 16777216,
  /* 2477 */ 33554432, 134217728, 268435456, 1073741824, 0, 0, 0, 123856, 1966080, 0, 64, 384, 16384, 65536, 131072,
  /* 2492 */ 16384, 65536, 524288, 268435456, 0x80000000, 0, 0, 524288, 0x80000000, 0, 0, 1, 16, 0, 256, 524288, 0, 0,
  /* 2510 */ 0, 25, 96, 128, -537854471, 0, 0, 0, 32, 7404800, -545259520, 0, 0, 0, 60, 0, 249, 64768, 1048576, 6291456,
  /* 2530 */ 6291456, 25165824, 100663296, 402653184, 1073741824, 96, 128, 1280, 2048, 4096, 57344, 6291456, 57344,
  /* 2543 */ 6291456, 8388608, 16777216, 33554432, 201326592, 1342177280, 0x80000000, 0, 57344, 6291456, 8388608,
  /* 2554 */ 100663296, 134217728, 0x80000000, 0, 0, 0, 1, 8, 16, 64, 128, 64, 128, 256, 1024, 131072, 131072, 131072,
  /* 2572 */ 262144, 524288, 16777216, 57344, 6291456, 8388608, 67108864, 134217728, 64, 256, 1024, 2048, 4096, 57344,
  /* 2586 */ 64, 256, 0, 24576, 32768, 6291456, 67108864, 134217728, 0, 1, 64, 256, 24576, 32768, 4194304, 32768,
  /* 2602 */ 4194304, 67108864, 0, 0, 64, 256, 0, 0, 24576, 32768, 0, 16384, 4194304, 67108864, 64, 16384, 0, 0, 1, 64,
  /* 2622 */ 256, 16384, 4194304, 67108864, 0, 0, 0, 16384, 0, 16384, 16384, 0, -470447874, -470447874, -470447874, 0,
  /* 2638 */ 0, 128, 0, 0, 8, 96, 2048, 32768, 262144, 8388608, 35056, 1376256, -471859200, 0, 0, 14, 16, 224, 2048,
  /* 2657 */ 32768, 2097152, 4194304, 8388608, -486539264, 0, 96, 128, 2048, 32768, 262144, 2097152, 262144, 2097152,
  /* 2671 */ 8388608, 33554432, 536870912, 1073741824, 0x80000000, 0, 1610612736, 0x80000000, 0, 0, 1, 524288, 1048576,
  /* 2684 */ 12582912, 0, 0, 0, 151311, 264503296, 2097152, 8388608, 33554432, 1610612736, 0x80000000, 262144, 8388608,
  /* 2697 */ 33554432, 536870912, 67108864, 4194304, 0, 4194304, 0, 4194304, 4194304, 0, 0, 524288, 8388608, 536870912,
  /* 2711 */ 1073741824, 0x80000000, 1, 4097, 8388609, 96, 2048, 32768, 1073741824, 0x80000000, 0, 96, 2048,
  /* 2724 */ 0x80000000, 0, 0, 96, 2048, 0, 0, 1, 12582912, 0, 0, 0, 0, 1641895695, 1641895695, 0, 0, 0, 249, 7404800,
  /* 2744 */ 15, 87808, 1835008, 1639972864, 0, 768, 5120, 16384, 65536, 1835008, 1835008, 12582912, 16777216,
  /* 2757 */ 1610612736, 0, 3, 4, 8, 768, 4096, 65536, 0, 0, 256, 512, 786432, 8, 256, 512, 4096, 16384, 1835008, 16384,
  /* 2777 */ 1835008, 12582912, 1610612736, 0, 0, 0, 256, 0, 0, 0, 4, 8, 16, 32, 1, 2, 8, 256, 16384, 524288, 16384,
  /* 2798 */ 524288, 1048576, 12582912, 1610612736, 0, 0, 0, 8388608, 0, 0, 0, 524288, 4194304, 0, 0, 0, 8388608,
  /* 2815 */ -548662288, -548662288, -548662288, 0, 0, 256, 16384, 65536, 520093696, -1073741824, 0, 0, 0, 16777216, 0,
  /* 2830 */ 16, 32, 960, 4096, 4980736, 520093696, 1073741824, 0, 32, 896, 4096, 57344, 1048576, 6291456, 8388608,
  /* 2845 */ 16777216, 100663296, 134217728, 268435456, 0x80000000, 0, 512, 786432, 4194304, 33554432, 134217728,
  /* 2856 */ 268435456, 0, 786432, 4194304, 134217728, 268435456, 0, 524288, 4194304, 268435456, 0, 0, 0, 0, 0, 4194304,
  /* 2872 */ 4194304, -540651761, 0, 0, 0, 2, 4, 8, 16, 96, 128, 264503296, -805306368, 0, 0, 0, 8, 256, 512, 19456,
  /* 2892 */ 131072, 3072, 16384, 131072, 262144, 8388608, 16777216, 512, 1024, 2048, 16384, 131072, 262144, 131072,
  /* 2906 */ 262144, 8388608, 33554432, 201326592, 268435456, 0, 3, 4, 256, 1024, 2048, 57344, 16384, 131072, 8388608,
  /* 2921 */ 33554432, 134217728, 268435456, 0, 3, 256, 1024, 16384, 131072, 33554432, 134217728, 1073741824,
  /* 2933 */ 0x80000000, 0, 0, 256, 524288, 0x80000000, 0, 3, 256, 33554432, 134217728, 1073741824, 0, 1, 2, 33554432,
  /* 2949 */ 1, 2, 134217728, 1073741824, 0, 1, 2, 134217728, 0, 0, 0, 64, 0, 0, 0, 16, 32, 896, 4096, 786432, 4194304,
  /* 2970 */ 16777216, 33554432, 201326592, 268435456, 1073741824, 0x80000000, 0, 0, 0, 15, 0, 4980736, 4980736,
  /* 2983 */ 4980736, 70460, 70460, 3478332, 0, 0, 1008, 4984832, 520093696, 60, 4864, 65536, 0, 0, 0, 12, 16, 32, 256,
  /* 3002 */ 512, 4096, 65536, 0, 0, 0, 67108864, 0, 0, 0, 12, 0, 256, 512, 65536, 0, 0, 1024, 512, 131072, 131072, 4,
  /* 3024 */ 16, 32, 65536, 0, 4, 16, 32, 0, 0, 0, 4, 16, 0, 0, 16384, 67108864, 0, 0, 1, 24, 96, 128, 256, 1024
];

JSONiqTokenizer.TOKEN =
[
  "(0)",
  "JSONChar",
  "JSONCharRef",
  "JSONPredefinedCharRef",
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
  "'$$'",
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

var JSONiqTokenizer = _dereq_('./JSONiqTokenizer').JSONiqTokenizer;
var Lexer = _dereq_('./lexer').Lexer;

var keys = 'NaN|after|allowing|ancestor|ancestor-or-self|and|append|array|as|ascending|at|attribute|base-uri|before|boundary-space|break|by|case|cast|castable|catch|child|collation|comment|constraint|construction|contains|context|continue|copy|copy-namespaces|count|decimal-format|decimal-separator|declare|default|delete|descendant|descendant-or-self|descending|digit|div|document|document-node|element|else|empty|empty-sequence|encoding|end|eq|every|except|exit|external|false|first|following|following-sibling|for|from|ft-option|function|ge|greatest|group|grouping-separator|gt|idiv|if|import|in|index|infinity|insert|instance|integrity|intersect|into|is|item|json|json-item|jsoniq|last|lax|le|least|let|loop|lt|minus-sign|mod|modify|module|namespace|namespace-node|ne|next|node|nodes|not|null|object|of|only|option|or|order|ordered|ordering|paragraphs|parent|pattern-separator|per-mille|percent|preceding|preceding-sibling|previous|processing-instruction|rename|replace|return|returning|revalidation|satisfies|schema|schema-attribute|schema-element|score|select|self|sentences|sliding|some|stable|start|strict|switch|text|then|times|to|treat|true|try|tumbling|type|typeswitch|union|unordered|updating|validate|value|variable|version|when|where|while|window|with|words|xquery|zero-digit'.split('|');
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
        { name: 'JSONPredefinedCharRef', token: 'constant.language.escape' },
        { name: 'JSONCharRef', token: 'constant.language.escape' },
        { name: 'JSONChar', token: 'string' }
    ]
};
    
exports.JSONiqLexer = function(){ return new Lexer(JSONiqTokenizer, Rules); };
},
{"./JSONiqTokenizer":1,"./lexer":3}],
3:[function(_dereq_,module,exports){
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
{}]},{},[2])
(2)

});