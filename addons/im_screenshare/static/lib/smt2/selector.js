/*
  Selector.js, an JavaScript implementation of a CSS3 Query Selector
  Copyright (C) 2009 Henrik Lindqvist <henrik.lindqvist@llamalab.com>
  
  This library is free software: you can redistribute it and/or modify
  it under the terms of the GNU Lesser General Public License as published 
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Lesser General Public License for more details.
  
  You should have received a copy of the GNU Lesser General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
/**
 * A JavaScript implementation of a CSS3 Query Selector.
 * <p>For more information, please visit 
 * <a href="http://www.w3.org/TR/css3-selectors/" target="_blank">http://www.w3.org/TR/css3-selectors/</a>.</p>
 * @class Selector
 * @version 0.6
 * @author Henrik Lindqvist &lt;<a href="mailto:henrik.lindqvist@llamalab.com">henrik.lindqvist@llamalab.com</a>&gt;
 */

new function () {
/**
 * Pre-compiles an Selector query.
 * <p>When creating a <code>new</code> instance of the <code>Selector</code>, the query are 
 * pre-compiled for later execution with a call to {@link exec}.</p>
 * <p>The constructor can also be called as a function, without the <code>new</code> keyword. Then 
 * the query is executed against the optional context element, otherwise current document.</p>
 * <h4>Example:</h4>
 * <pre>
 *   // Constructor syntax:
 *   new Selector('div > p').exec(document).forEach(function (e) {
 *     e.style.color = 'red';
 *   });
 *   // Or,  shorthand syntax:
 *   Selector('div > p', document).forEach(function (e) {
 *     e.style.color = 'red';
 *   });
 * </pre>
 * @constructor Selector
 * @param {string} pattern - selector pattern.
 * @param {optional Object} context - document or context element.
 */
function Selector (p, c) {
  if (!(this instanceof Selector)) return new Selector(p).exec(c);
  if (!qsa) this.exec = cache[p] || (cache[p] = new compile(p));
  this.pattern = p;
}
Selector.prototype = {
  constructor : Selector,
/**
 * Execute a selector query.
 * <h4>Example:</h4>
 * <pre>
 *   new Selector('div > p').exec(document).forEach(function (e) {
 *     e.style.color = 'red';
 *   });
 * </pre>
 * @function {Array} exec
 * @param {optional Object} context - document or context element, otherwise current document.
 * @returns Non-live <code>Array</code> with matching elements.
 */
  exec : function (c) {
    var pe = this.patchElement, pa = this.patchArray, p = this.pattern, r = pe
      ? map.call((c||d).querySelectorAll(p), pe, this)
      : Array.prototype.slice.call((c||d).querySelectorAll(p));
    return pa ? pa.call(this, r) : r;
  },
/**
 * Returns a string representing the query source pattern.
 * @function {string} toString
 * @returns source pattern.
 */
  toString : function () {
    return this.pattern;
  },
/**
 * Returns a string representing the source code of the Selector.
 * @function {string} toSource
 * @returns source code.
 */
  toSource : function () {
    return 'new Selector("'+this.pattern+'")';
  }
/**
 * Hook for patching result Element&rsquo;s.
 * <p>When using the {@link Selector} within you own framework you can add this function to 
 * extend the resulting <code>Element</code>&rsquo;s before they are returned by {@link exec}.
 * <p>This function is not defined by default, since calling it unneccesarily affects performance.</p>
 * @function {Element} patchElement
 * @param {Element} e - the result element.
 * @returns the patched <code>Element</code>.
 * @see patchArray
 */
  //patchElement : function (e) { return e; },
/**
 * Hook for patching result Array.
 * <p>When using the {@link Selector} within you own framework you can add this function to 
 * extend the resulting <code>Array</code> before it&rsquo;sthey are returned by {@link exec}.
 * <p>This function is not defined by default, since calling it unneccesarily affects performance.</p>
 * @function {Array} patchArray
 * @param {Array} a - the result array.
 * @returns the patched <code>Array</code>.
 * @see patchElement
 */
  //patchArray : function (a) { return a; }
};
window.Selector = Selector;
// ------------------------------------------ Private ------------------------------------------- //
function $ (s) {
  var a = arguments;
  return s.replace(/\$(\d)/g, function (m, i) { return a[i] });
}
with (navigator.userAgent) {
  var ie = indexOf('MSIE')  != -1 && indexOf('Opera') == -1,
      mz = indexOf('Gecko') != -1 && indexOf('KHTML') == -1,
      wk = indexOf('AppleWebKit') != -1;
}
var d    = document,
    de   = d.documentElement,
    qsa  = !!d.querySelectorAll,
    bcn  = !!d.getElementsByClassName,
    cnl  = !!de.children,
    cnlt = cnl && de.children.tags && !wk,
    ec   = !!de.contains,
    cdp  = !!de.compareDocumentPosition,
    si   = typeof de.sourceIndex == 'number',
    cache = {},
    cmp = {
       '=': 'if($1($2=="$3")){$5}',
      '^=': 'if($1((x=$2)&&!x.indexOf("$3"))){$5}',
      '*=': 'if($1((x=$2)&&x.indexOf("$3")!=-1)){$5}',
      '$=': 'if($1((x=$2)&&x.indexOf("$3",x.length-$4)!=-1)){$5}',
      '~=': 'if($1((x=$2)&&(y=x.indexOf("$3"))!=-1&&(x.charCodeAt(y-1)||32)==32&&(x.charCodeAt(y+$4)||32)==32)){$5}',
      '|=': 'if($1((x=$2)&&(x=="$3"||!x.indexOf("$3-")))){$5}'
    },
    /*
    cmp = {
       '=': 'if($1($2=="$3")){$5}',
      '^=': 'if($1((x=$2)&&!x.indexOf("$3"))){$5}',
      '*=': 'if($1((x=$2)&&x.indexOf("$3")!=-1)){$5}',
      '$=': 'if($1/$3$/.test($2)){$5}',
      '~=': 'if($1/(^|\\s)$3(\\s|$)/.test($2)){$5}',
      '|=': 'if($1/^$3(-|$)/.test($2)){$5}'
    },
    */
    map = Array.prototype.map || function (fn, tp) {
      var i = this.length, r = new Array(i);
      while (--i >= 0) r[i] = fn.call(tp, this[i], i, this);
      return r;
    };
with (d.implementation) {
  var me = d.addEventListener 
        && (hasFeature('MutationEvents','2.0') 
        ||  hasFeature('Events','2.0') && hasFeature('Core','2.0'));
}
Selector.guid = 0;
Selector.nthIndex = function (LLi, c, r, tp, tv) {
  var p = c.parentNode, ci = 'LLi#'+tv, pl = 'LLi$'+tv;
  if (!p) return Number.NaN;
  if (!c[ci] || c.LLi != LLi) {
    for (var n = p.firstChild, i = 0; n; n = n.nextSibling) {
      if (n[tp] == tv) {
        n[ci] = ++i;
        n.LLi = LLi;
      }
    }
    p[pl] = i;
  }
  return r ? 1 + p[pl] - c[ci] : c[ci];
};
/*
//TODO: srt to slow in wk
Selector.srcIndex = function (h, n) {
  var i = 0, x;
  do {
    if (x = n.previousSibling) {
      n = x;
      if (n.getElementsByTagName) {
        if (x = h[n.LLn]) return x + i + 1;
        i += n.getElementsByTagName('*').length + 1;
      }
    }
    else if (n = n.parentNode) i++;
  } while (n);
  return i;
}
Selector.srcIndex = function (h, n) {
  var i = -1, x;
  do {
    if (n.nodeType === 1) {
      i++;
      if (x = h[n.LLn]) return x + i;
    }
    if (x = n.previousSibling) do { n = x; } while (x = x.lastChild);
    else n = n.parentNode;
  } while (n);
  return i;
}
*/
if (me) {
  function fn (e) { 
    with (e.target) {
      if (nodeType !== 2) 
        ownerDocument.LLi = ++Selector.guid;
    }
  }
  d.addEventListener('DOMNodeInserted', fn, false);
  d.addEventListener('DOMNodeRemoved', fn, false);
}
if (ie) {
  var am = {
    acceptcharset: 'acceptCharset',
    accesskey:     'accessKey',
    cellpadding:   'cellPadding',
    cellspacing:   'cellSpacing',
    checked:       'defaultChecked',
    selected:      'defaultSelected',
    'class':       'className',
    colspan:       'colSpan',
    'for':         'htmlFor',
    frameborder:   'frameBorder',
    hspace:        'hSpace',
    longdesc:      'longDesc',
    marginwidth:   'marginWidth',
    marginheight:  'marginHeight',
    noresize:      'noResize',
    noshade:       'noShade',
    maxlength:     'maxLength',
    readonly:      'readOnly',
    rowspan:       'rowSpan',
    tabindex:      'tabIndex',
    usemap:        'useMap',
    valign:        'vAlign',
    vspace:        'vSpace'
  }, ab = {
    compact:  1,
    nowrap:   1,
    ismap:    1,
    declare:  1,
    noshade:  1,
    checked:  1,
    disabled: 1,
    readonly: 1,
    multiple: 1,
    selected: 1,
    noresize: 1,
    defer:    1
  };
}
function compile (qp) {
  this.dup = this.srt = this.idx = this.i = this.nqp = 0;
  with (this) {
    var js = '';
    do {
      i = nqp = 0;
      js += $('n=c;$1q:do{$2}while(false);', srt?'s=0;':'', type(qp, $(
        srt?'for(x=r.length;s<x;z=s+((x-s)/2)|0,($1)?s=z+1:x=z);if(s<r.length)r.splice(s++,0,$2);else r[s++]=$2;':'r[s++]=$2;',
        cdp?'r[z].compareDocumentPosition(n)&4':'h[r[z].LLn]<h[n.LLn]',
        'pe?pe.call(this,n):n'
      ), 0, '*'));
    } while (qp = nqp);
    js = $(
      'var r=[],s=0,n,x,y,z,d=c?c.ownerDocument||c.document||c:c=document,pe=this.patchElement,pa=this.patchArray$1$2;$3return pa?pa.call(this,r):r;',
      dup>0?',h={}':'',
      idx?me?',LLi=d.LLi||(d.LLi=++Selector.guid)':',LLi=++Selector.guid':'',
      js
    );
    //console.log(js);
    return new Function('c', js);
  }
}
compile.prototype = {
  type: function (qp, js, n, s, c) {
    with (this) {
      var m = /^\s*([\w-]+|\*)?(.*)/.exec(qp), t = m[1] || '*';
      if (!n && c==' ' && !dup) dup = 1;
      js = pred(m[2], js, n, t, c);
      switch (c) {
        case '>':
          return cnlt && t!='*'
               ? $('for(var n$1=n.children.tags("$2"),i$1=0;n=n$1[i$1++];){$3}', ++i, t, js)
               : $(cnl ? 'for(var n$1=n.children,i$1=0;n=n$1[i$1++];)$2{$3}'
                       : 'for(n=n.firstChild;n;n=n.nextSibling)$2{$3}', 
                   ++i, t!='*'?'if(n.nodeName==="'+t.toUpperCase()+'")':!cnl||ie?'if(n.nodeType===1)':'', js);
        case '+':
          return $('while(n=n.nextSibling)if(n.node$1){$2break}else if(n.nodeType===1)break;',
                   t=='*'?'Type===1':'Name==="'+t.toUpperCase()+'"', js);
        case '~': 
          return $('while(n=n.nextSibling)if(n.node$1){$3}else if(n.node$2)break;',
                   t=='*'?'Type===1':'Name==="'+t.toUpperCase()+'"',
                   s=='*'?'Type===1':'Name==="'+s.toUpperCase()+'"', js);
        default:
          return (typeof js == 'object') ? String(js) // handled by pred
               : n ? t=='*' ? js : $('if(n.nodeName!="$1"){$2}', t.toUpperCase(), js)
               : $('for(var n$1=n.getElementsByTagName("$2"),i$1=0;n=n$1[i$1++];)$3{$4}',
                   ++i, t, ie&&t=='*'?'if(n.nodeType===1)':'', js);
      }
    }
  },
  pred: function (qp, js, n, t, c) {
    with (this) {
      var m = /^([#\.])([\w-]+)(.*)/.exec(qp)
           || /^(\[)\s*([\w-]+)\s*(?:([~|^$*]?=)\s*(?:(['"])(.*?)\4|([\w-]+)))?\s*\](.*)/.exec(qp)
           || /^:(first|last|only)-(?:(child)|of-type)(.*)/.exec(qp)
           || /^:(nth)-(?:(last)-)?(?:(child)|of-type)\(\s*(?:(odd|even)|(-|\d*)n([+-]\d+)?|([1-9]\d*))\s*\)(.*)/.exec(qp) 
           || /^:(active|checked|(?:dis|en)abled|empty|focus|link|root|target)(.*)/.exec(qp)
           || /^:(lang)\(\s*(['"])?(.*?)\2\s*\)(.*)/.exec(qp)
           || (!n && /^:(not)\(\s*(.*)\s*\)(.*)/.exec(qp)), x = 0;
      if (!m) {
        if (m = /^\s*([+>~,\s])\s*(\S.*)/.exec(qp)) {
          if (m[1] != ',') return type(m[2], js, n, t, m[1]);
          nqp = m[2];
          dup = 2;
          //srt = 1;
        }
        else if (/\S/.test(qp)) throw new Error('Illegal query near: '+qp);
        return dup<1?js:$('if(!h[x=n.LLn||(n.LLn=++Selector.guid)]){h[x]=$1;$2}', 
                          !srt||cdp?'true':si?'n.sourceIndex':'Selector.srcIndex(h,n)', js);
      }
      if (!n && m[1]=='#' && dup!=2) dup = -1;
      js = pred(m[m.length-1], js, n, t, 1);
      switch (m[1]) {
        case '#':
          return uniq(js, n, t, c, ie, 'n.id', '"'+m[2]+'"', 'd.getElementById("'+m[2]+'")');
        case '.':
          return bcn && !n && (!c || c==' ') && (t=='*' || !mz)
               ? Object($('for(var n$1=n.getElementsByClassName("$2"),i$1=0;n=n$1[i$1++];)$3{$4}',
                          ++i, m[2], t=='*'?'':'if(n.nodeName==="'+t.toUpperCase()+'")', js))
               : $(cmp['~='], n?'!':'', 'n.className', x=m[2], x.length, js);
        case '[':
          return (x = m[3])
               ? $(cmp[x],
                   n?'!':'',
                   ie ? (x = m[2].toLowerCase()) == 'style' ? 'style.cssText.toLowerCase()'
                        : ab[x] ? 'n.'+x+'&&"'+x+'"' 
                        : 'n.getAttribute("'+(am[x]||x)+'",2)'
                      : 'n.getAttribute("'+m[2]+'")',
                   x=m[5]||m[6], x.length,
                   js
                 )
               : $(ie?'if($1((x=n.getAttributeNode("$2"))&&x.specified)){$3}':'if($1n.hasAttribute("$2")){$3}', 
                   n?'!':'', m[2], js);
        case 'active':
        case 'focus':
          return uniq(js, n, t, c, 0, 'n', 'd.activeElement');
        case 'checked':
          return $('if($1(n.checked||n.selected)){$2}', n?'!':'', js);
        case 'disabled':
          x = 1;
        case 'enabled':
          return $(
            'if(n.disabled===$1$2){$3}', 
            !!(x ^ n), 
            ie?'&&((x=n.nodeName)==="BUTTON"||x==="INPUT"||x==="OPTION"||x==="OPTGROUP"||x==="SELECT"||x==="TEXTAREA"':'', 
            js
          );
        case 'empty':   
          return $('for(x=n.firstChild;x&&x.nodeType>3;x=x.nextSibling);if($1x){$2}', n?'':'!', js);
        case 'first':
          return flo(js, n, m[2], 'previous');
        case 'lang':
          return $(cmp['|='], n?'!':'', 'n.lang', x=m[3], x.length, js);
        case 'last':
          return flo(js, n, m[2], 'next');
        case 'link':
          return $('if($1(n.nodeName==="A"&&n.href)){$2}', n?'!':'', js);
        case 'nth':       
          var a = m[4] ? 2 : m[5]=='-' ? -1 : m[7] ? 0 : m[5] ? m[5]-0 : 1,
              b = m[4]=='odd' ? 1 : (m[6]||m[7])-0 || 0;
          if (a==1) return js;
          if (a==0 && b==1) return flo(js, n, m[3], m[2]?'next':'previous');
          if (a==b) b = 0;
          if (b<0) b = a+b;
          idx = 1;
          return $('if($1(Selector.nthIndex(LLi,n,$2,"node$3",$4)$5)){$6}', 
                   n?'!':'', !!m[2], m[3]?'Type':'Name', m[3]?'1':'n.nodeName',
                   a<0 ? '<='+b : a ? '%'+a+'==='+b : '==='+b, js);
        case 'not':
          return type(m[2], js, 1, '*');
        case 'only':
          return flo(js, n, m[2]);
        case 'root':
          return uniq(js, n, t, c, 0, 'n', 'd.documentElement');
        case 'target':
          x = '(d.defaultView||d.parentWindow||window).location.hash.substr(1)';
          return uniq(js, n, t, c, ie, 'n.id', x, 'd.getElementById('+x+')');
      }
    }
  },
  uniq: function (js, n, t, c, d, p, v, w) {
    return (n || (c && c!=' ') || d)
      ? $(n?'if($1!==$2){$3}':'if($1===$2){$3break q}', p, v, js)
      : Object($(
            ec  ? 'if((x=$1)===n||!n.contains||n.contains(x))$2'
          : cdp ? 'if((x=$1)===n||!n.compareDocumentPosition||n.compareDocumentPosition(x)&16)$2'
          :       'for(x=y=$1;y;y=y.parentNode)if(y===n)$2',
          w||v, 
          t=='*'?'{n=x;'+js+'break q}':'{if((n=x).nodeName==="'+t.toUpperCase()+'"){'+js+'}break q}'
        ));
  },
  flo: function (js, n, t, s) {
    return $(s?'for($2x=n.$1Sibling;x&&x.node$3;x=x.$1Sibling);if($4x){$5}'
              :'for($2(x=n.parentNode)&&(x=x.firstChild);x&&(x.node$3||x===n);x=x.nextSibling);if($4x){$5}', 
             s, t?'':'y=n.nodeName,', t?'Type!==1':'Name!==y', n?'':'!', js);
  }
};

}
