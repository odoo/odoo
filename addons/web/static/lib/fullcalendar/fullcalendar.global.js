/*!
FullCalendar (Vanilla JS) v7.1.0
Docs & License: https://fullcalendar.io
(c) 2026 Adam Shaw
*/
var FullCalendar = (function (exports) {
  'use strict';

  var n$1,l$2,u$2,t$1,i$2,r$1,o$1,e$1,f$2,c$2,a$2,s$1,h,p$2,v$1,y,d={},w$1=[],_=/acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i,g$1=Array.isArray;function m$1(n,l){for(var u in l)n[u]=l[u];return n}function b(n){n&&n.parentNode&&n.parentNode.removeChild(n);}function k$1(l,u,t){var i,r,o,e={};for(o in u)"key"==o?i=u[o]:"ref"==o?r=u[o]:e[o]=u[o];if(arguments.length>2&&(e.children=arguments.length>3?n$1.call(arguments,2):t),"function"==typeof l&&null!=l.defaultProps)for(o in l.defaultProps)void 0===e[o]&&(e[o]=l.defaultProps[o]);return x(l,e,i,r,null)}function x(n,t,i,r,o){var e={type:n,props:t,key:i,ref:r,__k:null,__:null,__b:0,__e:null,__c:null,constructor:void 0,__v:null==o?++u$2:o,__i:-1,__u:0};return null==o&&null!=l$2.vnode&&l$2.vnode(e),e}function M$1(){return {current:null}}function S(n){return n.children}function C(n,l){this.props=n,this.context=l;}function $$1(n,l){if(null==l)return n.__?$$1(n.__,n.__i+1):null;for(var u;l<n.__k.length;l++)if(null!=(u=n.__k[l])&&null!=u.__e)return u.__e;return "function"==typeof n.type?$$1(n):null}function I(n){if(n.__P&&n.__d){var u=n.__v,t=u.__e,i=[],r=[],o=m$1({},u);o.__v=u.__v+1,l$2.vnode&&l$2.vnode(o),q$1(n.__P,o,u,n.__n,n.__P.namespaceURI,32&u.__u?[t]:null,i,null==t?$$1(u):t,!!(32&u.__u),r),o.__v=u.__v,o.__.__k[o.__i]=o,D(i,o,r),u.__e=u.__=null,o.__e!=t&&P$1(o);}}function P$1(n){if(null!=(n=n.__)&&null!=n.__c)return n.__e=n.__c.base=null,n.__k.some(function(l){if(null!=l&&null!=l.__e)return n.__e=n.__c.base=l.__e}),P$1(n)}function A(n){(!n.__d&&(n.__d=!0)&&i$2.push(n)&&!H$1.__r++||r$1!=l$2.debounceRendering)&&((r$1=l$2.debounceRendering)||o$1)(H$1);}function H$1(){try{for(var n,l=1;i$2.length;)i$2.length>l&&i$2.sort(e$1),n=i$2.shift(),l=i$2.length,I(n);}finally{i$2.length=H$1.__r=0;}}function L(n,l,u,t,i,r,o,e,f,c,a){var s,h,p,v,y,_,g=t&&t.__k||w$1,m=l.length;for(f=T$1(u,l,g,f,m),s=0;s<m;s++)null!=(p=u.__k[s])&&(h=-1!=p.__i&&g[p.__i]||d,p.__i=s,_=q$1(n,p,h,i,r,o,e,f,c,a),v=p.__e,p.ref&&h.ref!=p.ref&&(h.ref&&J$1(h.ref,null,p),a.push(p.ref,p.__c||v,p)),null==y&&null!=v&&(y=v),4&p.__u?(f=j$2(p,f,n),h.__e&&(h.__e=null)):"function"==typeof p.type&&void 0!==_?f=_:v&&(f=v.nextSibling),p.__u&=-7);return u.__e=y,f}function T$1(n,l,u,t,i){var r,o,e,f,c,a=u.length,s=a,h=0;for(n.__k=new Array(i),r=0;r<i;r++)null!=(o=l[r])&&"boolean"!=typeof o&&"function"!=typeof o?("string"==typeof o||"number"==typeof o||"bigint"==typeof o||o.constructor==String?o=n.__k[r]=x(null,o,null,null,null):g$1(o)?o=n.__k[r]=x(S,{children:o},null,null,null):void 0===o.constructor&&o.__b>0?o=n.__k[r]=x(o.type,o.props,o.key,o.ref?o.ref:null,o.__v):n.__k[r]=o,f=r+h,o.__=n,o.__b=n.__b+1,e=null,-1!=(c=o.__i=O$1(o,u,f,s))&&(s--,(e=u[c])&&(e.__u|=2)),null==e||null==e.__v?(-1==c&&(i>a?h--:i<a&&h++),"function"!=typeof o.type&&(o.__u|=4)):c!=f&&(c==f-1?h--:c==f+1?h++:(c>f?h--:h++,o.__u|=4))):n.__k[r]=null;if(s)for(r=0;r<a;r++)null!=(e=u[r])&&0==(2&e.__u)&&(e.__e==t&&(t=$$1(e)),K$1(e,e));return t}function j$2(n,l,u){var t,i;if("function"==typeof n.type){for(t=n.__k,i=0;t&&i<t.length;i++)t[i]&&(t[i].__=n,l=j$2(t[i],l,u));return l}n.__e!=l&&(l&&n.type&&!l.parentNode&&(l=$$1(n)),l=u.insertBefore(n.__e,l||null));do{l=l&&l.nextSibling;}while(null!=l&&8==l.nodeType);return l}function F(n,l){return l=l||[],null==n||"boolean"==typeof n||(g$1(n)?n.some(function(n){F(n,l);}):l.push(n)),l}function O$1(n,l,u,t){var i,r,o,e=n.key,f=n.type,c=l[u],a=null!=c&&0==(2&c.__u);if(null===c&&null==e||a&&e==c.key&&f==c.type)return u;if(t>(a?1:0))for(i=u-1,r=u+1;i>=0||r<l.length;)if(null!=(c=l[o=i>=0?i--:r++])&&0==(2&c.__u)&&e==c.key&&f==c.type)return o;return -1}function z$1(n,l,u){"-"==l[0]?n.setProperty(l,null==u?"":u):n[l]=null==u?"":"number"!=typeof u||_.test(l)?u:u+"px";}function N(n,l,u,t,i){var r,o;n:if("style"==l)if("string"==typeof u)n.style.cssText=u;else {if("string"==typeof t&&(n.style.cssText=t=""),t)for(l in t)u&&l in u||z$1(n.style,l,"");if(u)for(l in u)t&&u[l]==t[l]||z$1(n.style,l,u[l]);}else if("o"==l[0]&&"n"==l[1])r=l!=(l=l.replace(s$1,"$1")),o=l.toLowerCase(),l=o in n||"onFocusOut"==l||"onFocusIn"==l?o.slice(2):l.slice(2),n.l||(n.l={}),n.l[l+r]=u,u?t?u[a$2]=t[a$2]:(u[a$2]=h,n.addEventListener(l,r?v$1:p$2,r)):n.removeEventListener(l,r?v$1:p$2,r);else {if("http://www.w3.org/2000/svg"==i)l=l.replace(/xlink(H|:h)/,"h").replace(/sName$/,"s");else if("width"!=l&&"height"!=l&&"href"!=l&&"list"!=l&&"form"!=l&&"tabIndex"!=l&&"download"!=l&&"rowSpan"!=l&&"colSpan"!=l&&"role"!=l&&"popover"!=l&&l in n)try{n[l]=null==u?"":u;break n}catch(n){}"function"==typeof u||(null==u||!1===u&&"-"!=l[4]?n.removeAttribute(l):n.setAttribute(l,"popover"==l&&1==u?"":u));}}function V$1(n){return function(u){if(this.l){var t=this.l[u.type+n];if(null==u[c$2])u[c$2]=h++;else if(u[c$2]<t[a$2])return;return t(l$2.event?l$2.event(u):u)}}}function q$1(n,u,t,i,r,o,e,f,c,a){var s,h,p,v,y,d,_,k,x,M,I,P,A,H,T,j,F=u.type;if(void 0!==u.constructor)return null;128&t.__u&&(c=!!(32&t.__u),o=[f=u.__e=t.__e]),(s=l$2.__b)&&s(u);n:if("function"==typeof F){h=e.length;try{if(x=u.props,M=F.prototype&&F.prototype.render,I=(s=F.contextType)&&i[s.__c],P=s?I?I.props.value:s.__:i,t.__c?k=(p=u.__c=t.__c).__=p.__E:(M?u.__c=p=new F(x,P):(u.__c=p=new C(x,P),p.constructor=F,p.render=Q$1),I&&I.sub(p),p.state||(p.state={}),p.__n=i,v=p.__d=!0,p.__h=[],p._sb=[]),M&&null==p.__s&&(p.__s=p.state),M&&null!=F.getDerivedStateFromProps&&(p.__s==p.state&&(p.__s=m$1({},p.__s)),m$1(p.__s,F.getDerivedStateFromProps(x,p.__s))),y=p.props,d=p.state,p.__v=u,v)M&&null==F.getDerivedStateFromProps&&null!=p.componentWillMount&&p.componentWillMount(),M&&null!=p.componentDidMount&&p.__h.push(p.componentDidMount);else {if(M&&null==F.getDerivedStateFromProps&&x!==y&&null!=p.componentWillReceiveProps&&p.componentWillReceiveProps(x,P),u.__v==t.__v||!p.__e&&null!=p.shouldComponentUpdate&&!1===p.shouldComponentUpdate(x,p.__s,P)){u.__v!=t.__v&&(p.props=x,p.state=p.__s,p.__d=!1),u.__e=t.__e,u.__k=t.__k,u.__k.some(function(n){n&&(n.__=u);}),w$1.push.apply(p.__h,p._sb),p._sb=[],p.__h.length&&e.push(p),f=$$1(t);break n}null!=p.componentWillUpdate&&p.componentWillUpdate(x,p.__s,P),M&&null!=p.componentDidUpdate&&p.__h.push(function(){p.componentDidUpdate(y,d,_);});}if(p.context=P,p.props=x,p.__P=n,p.__e=!1,A=l$2.__r,H=0,M)p.state=p.__s,p.__d=!1,A&&A(u),s=p.render(p.props,p.state,p.context),w$1.push.apply(p.__h,p._sb),p._sb=[];else do{p.__d=!1,A&&A(u),s=p.render(p.props,p.state,p.context),p.state=p.__s;}while(p.__d&&++H<25);p.state=p.__s,null!=p.getChildContext&&(i=m$1(m$1({},i),p.getChildContext())),M&&!v&&null!=p.getSnapshotBeforeUpdate&&(_=p.getSnapshotBeforeUpdate(y,d)),T=null!=s&&s.type===S&&null==s.key?E$1(s.props.children):s,f=L(n,g$1(T)?T:[T],u,t,i,r,o,e,f,c,a),p.base=u.__e,u.__u&=-161,p.__h.length&&e.push(p),k&&(p.__E=p.__=null);}catch(n){if(e.length=h,u.__v=null,c||null!=o){if(n.then){for(u.__u|=c?160:128;f&&8==f.nodeType&&f.nextSibling;)f=f.nextSibling;null!=o&&(o[o.indexOf(f)]=null),u.__e=f;}else if(null!=o)for(j=o.length;j--;)b(o[j]);}else u.__e=t.__e;null==u.__k&&(u.__k=t.__k||[]),n.then||B$2(u),l$2.__e(n,u,t);}}else null==o&&u.__v==t.__v?(u.__k=t.__k,u.__e=t.__e):f=u.__e=G$1(t.__e,u,t,i,r,o,e,c,a);return (s=l$2.diffed)&&s(u),128&u.__u?void 0:f}function B$2(n){n&&(n.__c&&(n.__c.__e=!0),n.__k&&n.__k.some(B$2));}function D(n,u,t){for(var i=0;i<t.length;i++)J$1(t[i],t[++i],t[++i]);l$2.__c&&l$2.__c(u,n),n.some(function(u){try{n=u.__h,u.__h=[],n.some(function(n){n.call(u);});}catch(n){l$2.__e(n,u.__v);}});}function E$1(n){return "object"!=typeof n||null==n||n.__b>0?n:g$1(n)?n.map(E$1):void 0!==n.constructor?null:m$1({},n)}function G$1(u,t,i,r,o,e,f,c,a){var s,h,p,v,y,w,_,m=i.props||d,k=t.props,x=t.type;if("svg"==x?o="http://www.w3.org/2000/svg":"math"==x?o="http://www.w3.org/1998/Math/MathML":o||(o="http://www.w3.org/1999/xhtml"),null!=e)for(s=0;s<e.length;s++)if((y=e[s])&&"setAttribute"in y==!!x&&(x?y.localName==x:3==y.nodeType)){u=y,e[s]=null;break}if(null==u){if(null==x)return document.createTextNode(k);u=document.createElementNS(o,x,k.is&&k),c&&(l$2.__m&&l$2.__m(t,e),c=!1),e=null;}if(null==x)m===k||c&&u.data==k||(u.data=k);else {if(e="textarea"==x&&null!=k.defaultValue?null:e&&n$1.call(u.childNodes),!c&&null!=e)for(m={},s=0;s<u.attributes.length;s++)m[(y=u.attributes[s]).name]=y.value;for(s in m)y=m[s],"dangerouslySetInnerHTML"==s?p=y:"children"==s||s in k||"value"==s&&"defaultValue"in k||"checked"==s&&"defaultChecked"in k||N(u,s,null,y,o);for(s in k)y=k[s],"children"==s?v=y:"dangerouslySetInnerHTML"==s?h=y:"value"==s?w=y:"checked"==s?_=y:c&&"function"!=typeof y||m[s]===y||N(u,s,y,m[s],o);if(h)c||p&&(h.__html==p.__html||h.__html==u.innerHTML)||(u.innerHTML=h.__html),t.__k=[];else if(p&&(u.innerHTML=""),L("template"==t.type?u.content:u,g$1(v)?v:[v],t,i,r,"foreignObject"==x?"http://www.w3.org/1999/xhtml":o,e,f,e?e[0]:i.__k&&$$1(i,0),c,a),null!=e)for(s=e.length;s--;)b(e[s]);c&&"textarea"!=x||(s="value","progress"==x&&null==w?u.removeAttribute("value"):null!=w&&(w!==u[s]||"progress"==x&&!w||"option"==x&&w!=m[s])&&N(u,s,w,m[s],o),s="checked",null!=_&&_!=u[s]&&N(u,s,_,m[s],o));}return u}function J$1(n,u,t){try{if("function"==typeof n){var i="function"==typeof n.__u;i&&n.__u(),i&&null==u||(n.__u=n(u));}else n.current=u;}catch(n){l$2.__e(n,t);}}function K$1(n,u,t){var i,r;if(l$2.unmount&&l$2.unmount(n),(i=n.ref)&&(i.current&&i.current!=n.__e||J$1(i,null,u)),null!=(i=n.__c)){if(i.componentWillUnmount)try{i.componentWillUnmount();}catch(n){l$2.__e(n,u);}i.base=i.__P=i.__n=null;}if(i=n.__k)for(r=0;r<i.length;r++)i[r]&&K$1(i[r],u,t||"function"!=typeof n.type);t||b(n.__e),n.__c=n.__=n.__e=void 0;}function Q$1(n,l,u){return this.constructor(n,u)}function R(u,t,i){var r,o,e,f;t==document&&(t=document.documentElement),l$2.__&&l$2.__(u,t),o=(r="function"==typeof i)?null:i&&i.__k||t.__k,e=[],f=[],q$1(t,u=(!r&&i||t).__k=k$1(S,null,[u]),o||d,d,t.namespaceURI,!r&&i?[i]:o?null:t.firstChild?n$1.call(t.childNodes):null,e,!r&&i?i:o?o.__e:t.firstChild,r,f),D(e,u,f),u.props.children=null;}function U$1(n,l){R(n,l,U$1);}function W$1(l,u,t){var i,r,o,e,f=m$1({},l.props);for(o in l.type&&l.type.defaultProps&&(e=l.type.defaultProps),u)"key"==o?i=u[o]:"ref"==o?r=u[o]:f[o]=void 0===u[o]&&null!=e?e[o]:u[o];return arguments.length>2&&(f.children=arguments.length>3?n$1.call(arguments,2):t),x(l.type,f,i||l.key,r||l.ref,null)}function X$1(n){function l(n){var u,t;return this.getChildContext||(u=new Set,(t={})[l.__c]=this,this.getChildContext=function(){return t},this.componentWillUnmount=function(){u=null;},this.shouldComponentUpdate=function(n){this.props.value!=n.value&&u.forEach(function(n){n.__e=!0,A(n);});},this.sub=function(n){u.add(n);var l=n.componentWillUnmount;n.componentWillUnmount=function(){u&&u.delete(n),l&&l.call(n);};}),n.children}return l.__c="__cC"+y++,l.__=n,l.Provider=l.__l=(l.Consumer=function(n,l){return n.children(l)}).contextType=l,l}n$1=w$1.slice,l$2={__e:function(n,l,u,t){for(var i,r,o;l=l.__;)if((i=l.__c)&&!i.__)try{if((r=i.constructor)&&null!=r.getDerivedStateFromError&&(i.setState(r.getDerivedStateFromError(n)),o=i.__d),null!=i.componentDidCatch&&(i.componentDidCatch(n,t||{}),o=i.__d),o)return i.__E=i}catch(l){n=l;}throw n}},u$2=0,t$1=function(n){return null!=n&&void 0===n.constructor},C.prototype.setState=function(n,l){var u;u=null!=this.__s&&this.__s!=this.state?this.__s:this.__s=m$1({},this.state),"function"==typeof n&&(n=n(m$1({},u),this.props)),n&&m$1(u,n),null!=n&&this.__v&&(l&&this._sb.push(l),A(this));},C.prototype.forceUpdate=function(n){this.__v&&(this.__e=!0,n&&this.__h.push(n),A(this));},C.prototype.render=S,i$2=[],o$1="function"==typeof Promise?Promise.prototype.then.bind(Promise.resolve()):setTimeout,e$1=function(n,l){return n.__v.__b-l.__v.__b},H$1.__r=0,f$2=Math.random().toString(8),c$2="__d"+f$2,a$2="__a"+f$2,s$1=/(PointerCapture)$|Capture$/i,h=0,p$2=V$1(!1),v$1=V$1(!0),y=0;

  var preact = /*#__PURE__*/Object.freeze({
      __proto__: null,
      Component: C,
      Fragment: S,
      cloneElement: W$1,
      createContext: X$1,
      createElement: k$1,
      createRef: M$1,
      h: k$1,
      hydrate: U$1,
      get isValidElement () { return t$1; },
      get options () { return l$2; },
      render: R,
      toChildArray: F
  });

  var t=/["&<]/;function n(r){if(0===r.length||!1===t.test(r))return r;for(var e=0,n=0,o="",f="";n<r.length;n++){switch(r.charCodeAt(n)){case 34:f="&quot;";break;case 38:f="&amp;";break;case 60:f="&lt;";break;default:continue}n!==e&&(o+=r.slice(e,n)),o+=f,e=n+1;}return n!==e&&(o+=r.slice(e,n)),o}var o=/acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i,f$1=0,i$1=Array.isArray;function u$1(e,t,n,o,i,u){t||(t={});var a,c,p=t;if("ref"in p)for(c in p={},t)"ref"==c?a=t[c]:p[c]=t[c];var l={type:e,props:p,key:n,ref:a,__k:null,__:null,__b:0,__e:null,__c:null,constructor:void 0,__v:--f$1,__i:-1,__u:0,__source:i,__self:u};if("function"==typeof e&&(a=e.defaultProps))for(c in a)void 0===p[c]&&(p[c]=a[c]);return l$2.vnode&&l$2.vnode(l),l}function a$1(r){var t=u$1(S,{tpl:r,exprs:[].slice.call(arguments,1)});return t.key=t.__v,t}var c$1={},p$1=/[A-Z]/g;function l$1(e,t){if(l$2.attr){var f=l$2.attr(e,t);if("string"==typeof f)return f}if(t=function(r){return null!==r&&"object"==typeof r&&"function"==typeof r.valueOf?r.valueOf():r}(t),"ref"===e||"key"===e)return "";if("style"===e&&"object"==typeof t){var i="";for(var u in t){var a=t[u];if(null!=a&&""!==a){var l="-"==u[0]?u:c$1[u]||(c$1[u]=u.replace(p$1,"-$&").toLowerCase()),s=";";"number"!=typeof a||l.startsWith("--")||o.test(l)||(s="px;"),i=i+l+":"+a+s;}}return e+'="'+n(i)+'"'}return null==t||!1===t||"function"==typeof t||"object"==typeof t?"":!0===t?e:e+'="'+n(""+t)+'"'}function s(r){if(null==r||"boolean"==typeof r||"function"==typeof r)return null;if("object"==typeof r){if(void 0===r.constructor)return r;if(i$1(r)){for(var e=0;e<r.length;e++)r[e]=s(r[e]);return r}}return n(""+r)}

  var jsxRuntime = /*#__PURE__*/Object.freeze({
      __proto__: null,
      jsx: u$1,
      jsxAttr: l$1,
      jsxDEV: u$1,
      jsxEscape: s,
      jsxTemplate: a$1,
      jsxs: u$1,
      Fragment: S
  });

  const NativeTemporal = globalThis.Temporal;
  const expectedFinite = (entityName, num) => `Non-finite ${entityName}: ${num}`;
  const forbiddenBigIntToNumber = (entityName) => `Cannot convert bigint to ${entityName}`;
  const invalidObject = 'Invalid object';
  const numberOutOfRange = (entityName, val, min, max) => invalidEntity$1(entityName, val) + `; must be between ${min}-${max}`;
  // Entity/Fields/Bags
  const invalidEntity$1 = (fieldName, val) => `Invalid ${fieldName}: ${val}`;

  const nanoInMicro$1 = 1_000;
  const nanoInMilli$1 = 1_000_000;
  const nanoInSec$1 = 1_000_000_000;
  const nanoInMinute$1 = 60_000_000_000;
  const nanoInHour$1 = 3_600_000_000_000;
  function normalizeOptions(options) {
      if (options === undefined) {
          return Object.create(null);
      }
      return requireObjectLike(options);
  }
  function toFiniteNumber(arg, entityName = 'number') {
      if (typeof arg === 'bigint') {
          throw new TypeError(forbiddenBigIntToNumber(entityName));
      }
      arg = Number(arg);
      if (!Number.isFinite(arg)) {
          throw new RangeError(expectedFinite(entityName, arg));
      }
      return arg;
  }
  function toIntegerWithTrunc(arg, entityName) {
      return Math.trunc(toFiniteNumber(arg, entityName)) || 0; // ensure no -0
  }
  /*
  min/max are inclusive
  */
  function constrainToRange$1(num, min, max) {
      return Math.min(Math.max(num, min), max);
  }
  function isObjectLike(arg) {
      return arg !== null && (typeof arg === 'object' || typeof arg === 'function');
  }
  function requireObjectLike(arg) {
      if (!isObjectLike(arg)) {
          throw new TypeError(invalidObject);
      }
      return arg;
  }

  const invalidEntity = invalidEntity$1;

  const missingField = fieldName => `Missing ${fieldName}`;

  const invalidChoice = (fieldName, val, choiceMap) => invalidEntity$1(fieldName, val) + "; must be " + Object.keys(choiceMap).join();

  const forbiddenValueOf$1 = "Cannot use valueOf";

  const invalidCallingContext = "Invalid calling context";

  const exoticCalendarRequired = (calendarId, remedy) => `Unknown calendar ${calendarId}; might need ${remedy}`;

  const invalidTimeZone = calendarId => invalidEntity$1("TimeZone", calendarId);

  const outOfBoundsDate = "Out-of-bounds date";

  const invalidSubstring = substring => `Invalid substring: ${substring}`;

  const constrainToRange = constrainToRange$1;

  function throwRangeError(message) {
    throw new RangeError(message);
  }

  function throwTypeError(message) {
    throw new TypeError(message);
  }

  function clampProp(props, propName, min, max, overflow) {
    return clampEntity(propName, ((props, propName) => {
      const propVal = props[propName];
      return void 0 === propVal && throwTypeError(missingField(propName)), propVal;
    })(props, propName), min, max, overflow);
  }

  function clampEntity(entityName, num, min, max, overflow, choices) {
    const clamped = constrainToRange(num, min, max);
    return overflow && num !== clamped && throwRangeError(((entityName, val, min, max, choices) => choices ? numberOutOfRange(entityName, choices[val], choices[min], choices[max]) : numberOutOfRange(entityName, val, min, max))(entityName, num, min, max, choices)), 
    clamped;
  }

  function memoize$1(generator, MapClass = Map) {
    const map = new MapClass;
    return (key, ...otherArgs) => {
      if (map.has(key)) {
        return map.get(key);
      }
      const val = generator(key, ...otherArgs);
      return map.set(key, val), val;
    };
  }

  const createNameDescriptors = name => createPropDescriptors({
    name: name
  }, 1);

  const createPropDescriptors = (propVals, readonly) => mapProps(value => ({
    value: value,
    configurable: 1,
    writable: !readonly
  }), propVals);

  const createStringTagDescriptors = value => ({
    [Symbol.toStringTag]: {
      value: value,
      configurable: 1
    }
  });

  function mapProps(transformer, props) {
    const res = {};
    for (const propName in props) {
      res[propName] = transformer(props[propName], propName);
    }
    return res;
  }

  function createPropGetters(propNames) {
    const getters = {};
    for (const propName of propNames) {
      getters[propName] = slots => slots[propName];
    }
    return getters;
  }

  function pluckProps(propNames, props, dest = Object.create(null)) {
    for (const propName of propNames) {
      dest[propName] = props[propName];
    }
    return dest;
  }

  function bindArgs(f, ...boundArgs) {
    return (...dynamicArgs) => f(...boundArgs, ...dynamicArgs);
  }

  function noop() {}

  function capitalize(s) {
    return s[0].toUpperCase() + s.substring(1);
  }

  function createRegExp(meat) {
    return new RegExp(`^${meat}$`, "i");
  }

  function parseSubsecNano(fracStr) {
    return parseInt(fracStr.padEnd(9, "0"));
  }

  function parseSign(s) {
    return s && "+" !== s ? -1 : 1;
  }

  function parseInt0(s) {
    return void 0 === s ? 0 : parseInt(s);
  }

  function padNumber(digits, num) {
    return String(num).padStart(digits, "0");
  }

  const padNumber2 = /*@__PURE__*/ bindArgs(padNumber, 2);

  function compareNumbers$1(a, b) {
    return Math.sign(a - b);
  }

  function divFloorBigInt(num, denom) {
    const whole = num / denom;
    return num % denom < 0n ? whole - 1n : whole;
  }

  function divModFloorBigInt(num, divisor) {
    const quotient = divFloorBigInt(num, divisor);
    return [ quotient, num - quotient * divisor ];
  }

  function divModFloor(num, divisor) {
    return [ Math.floor(num / divisor), modFloor(num, divisor) ];
  }

  function modFloor(num, divisor) {
    return (num % divisor + divisor) % divisor;
  }

  function divTrunc(num, divisor) {
    return Math.trunc(num / divisor) || 0;
  }

  function hasHalf(num) {
    return .5 === Math.abs(num % 1);
  }

  function normalizeEraName(era) {
    const normalized = era.normalize("NFD").toLowerCase().replace(/[^a-z0-9]/g, "");
    return "bc" === normalized || "b" === normalized ? "bce" : "ad" === normalized || "a" === normalized ? "ce" : normalized;
  }

  const isoCalendarImpl = void 0;

  function getCalendarSlotId(calendar) {
    return calendar === isoCalendarImpl ? "iso8601" : 0 === calendar ? "gregory" : calendar.id;
  }

  function formatMonthCode(monthCodeNumber, isLeapMonth) {
    return "M" + padNumber2(monthCodeNumber) + (isLeapMonth ? "L" : "");
  }

  const unitNameMap = {
    nanosecond: 0,
    microsecond: 1,
    millisecond: 2,
    second: 3,
    minute: 4,
    hour: 5,
    day: 6,
    week: 7,
    month: 8,
    year: 9
  };

  const unitNamesAsc = /*@__PURE__*/ Object.keys(unitNameMap);

  const nanoInMicro = nanoInMicro$1;

  const nanoInMilli = nanoInMilli$1;

  const nanoInSec = nanoInSec$1;

  const nanoInMinute = nanoInMinute$1;

  const nanoInHour = nanoInHour$1;

  const nanoInUtcDay = 864e11;

  const bigNanoInMilli = /*@__PURE__*/ BigInt(nanoInMilli);

  const bigNanoInSec = /*@__PURE__*/ BigInt(nanoInSec);

  const bigNanoInUtcDay = /*@__PURE__*/ BigInt(nanoInUtcDay);

  const timeFieldNamesAsc = /*@__PURE__*/ unitNamesAsc.slice(0, 6);

  const timeGetters$1 = /*@__PURE__*/ createPropGetters(timeFieldNamesAsc);

  const calendarDateFieldNamesAsc = [ "day", "month", "year" ];

  function validateTimeFields(timeFields) {
    return constrainTimeFields(timeFields, 1), timeFields;
  }

  const maxValues = {
    hour: 23,
    minute: 59,
    second: 59
  };

  function constrainTimeFields(timeFields, overflow) {
    const constrainedFields = {};
    for (const fieldName of timeFieldNamesAsc) {
      constrainedFields[fieldName] = clampEntity(fieldName, timeFields[fieldName], 0, maxValues[fieldName] || 999, overflow);
    }
    return constrainedFields;
  }

  function timeFieldsToNano(timeFields) {
    return timeFieldsToSec(timeFields) * nanoInSec + timeFieldsToSubsecNano(timeFields);
  }

  function timeFieldsToSec(timeFields) {
    return 3600 * timeFields.hour + 60 * timeFields.minute + timeFields.second;
  }

  function timeFieldsToSubsecNano(timeFields) {
    return timeFields.millisecond * nanoInMilli + timeFields.microsecond * nanoInMicro + timeFields.nanosecond;
  }

  function nanoToTimeFields(timeNano) {
    const [timeMilli, nanoAfterMilli] = divModFloor(timeNano, nanoInMilli);
    const [microsecond, nanosecond] = divModFloor(nanoAfterMilli, nanoInMicro);
    return milliToTimeFields(timeMilli, microsecond, nanosecond);
  }

  function milliToTimeFields(timeMilli, microsecond = 0, nanosecond = 0) {
    const [hour, milliAfterHour] = divModFloor(timeMilli, 36e5);
    const [minute, milliAfterMinute] = divModFloor(milliAfterHour, 6e4);
    const [second, millisecond] = divModFloor(milliAfterMinute, 1e3);
    return {
      hour: hour,
      minute: minute,
      second: second,
      millisecond: millisecond,
      microsecond: microsecond,
      nanosecond: nanosecond
    };
  }

  function epochNanoToSecMod(epochNano) {
    const [epochSec, nano] = divModFloorBigInt(epochNano, bigNanoInSec);
    return [ Number(epochSec), Number(nano) ];
  }

  function isoDateTimeToEpochNano(isoDateTime) {
    return isoDateToEpochNano(isoDateTime) + BigInt(timeFieldsToNano(isoDateTime));
  }

  function isoDateToEpochNano(isoDate) {
    return BigInt(isoDateToEpochDays(isoDate)) * bigNanoInUtcDay;
  }

  function isoDateToEpochDays(isoDate) {
    return isoArgsToEpochDays(isoDate.year, isoDate.month, isoDate.day);
  }

  function isoArgsToEpochDays(isoYear, isoMonth = 1, isoDay = 1) {
    const monthIndex = isoMonth - 1;
    return isoYear += Math.floor(monthIndex / 12), isoMonth = modFloor(monthIndex, 12), 
    Date.UTC(isoYear % 400 - 400, isoMonth, 0) / 864e5 + 146097 * (divTrunc(isoYear, 400) + 1) + isoDay;
  }

  function epochNanoToIsoDateTime(epochNano) {
    const [epochDays, nanoAfterDay] = divModFloorBigInt(epochNano, bigNanoInUtcDay);
    return {
      ...epochDaysToIsoDate(Number(epochDays)),
      ...nanoToTimeFields(Number(nanoAfterDay))
    };
  }

  function epochDaysToIsoDate(epochDays) {
    const legacyDate = new Date(864e5 * modFloor(epochDays, 146097));
    return {
      year: legacyDate.getUTCFullYear() + 400 * Math.floor(epochDays / 146097),
      month: legacyDate.getUTCMonth() + 1,
      day: legacyDate.getUTCDate()
    };
  }

  function computeIsoMonthCodeParts(month) {
    return [ month, 0 ];
  }

  function computeIsoFieldsFromParts(year, month, day) {
    return {
      year: year,
      month: month,
      day: day
    };
  }

  function computeIsoDaysInMonth(year, month) {
    switch (month) {
     case 2:
      return computeIsoInLeapYear(year) ? 29 : 28;

     case 4:
     case 6:
     case 9:
     case 11:
      return 30;
    }
    return 31;
  }

  function computeIsoDaysInYear(year) {
    return computeIsoInLeapYear(year) ? 366 : 365;
  }

  function computeIsoInLeapYear(year) {
    return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
  }

  function computeIsoDayOfWeek(isoDateFields) {
    return modFloor(isoArgsToEpochDays(isoDateFields.year, isoDateFields.month, isoDateFields.day) + 4, 7) || 7;
  }

  function computeIsoDayOfYear(isoDateFields) {
    return isoArgsToEpochDays(isoDateFields.year, isoDateFields.month, isoDateFields.day) - isoArgsToEpochDays(isoDateFields.year) + 1;
  }

  function computeIsoWeekFields(isoDateFields) {
    let yearOfWeek = isoDateFields.year;
    let weekOfYear = Math.floor((computeIsoDayOfYear(isoDateFields) - computeIsoDayOfWeek(isoDateFields) + 10) / 7);
    let weeksInYear = computeIsoWeeksInYear(yearOfWeek);
    return weekOfYear < 1 ? weekOfYear = weeksInYear = computeIsoWeeksInYear(--yearOfWeek) : weekOfYear > weeksInYear && (weekOfYear = 1, 
    weeksInYear = computeIsoWeeksInYear(++yearOfWeek)), {
      weekOfYear: weekOfYear,
      yearOfWeek: yearOfWeek,
      Ie: weeksInYear
    };
  }

  function computeIsoWeeksInYear(year) {
    const y0DayOfWeek = computeIsoDayOfWeek({
      year: year,
      month: 1,
      day: 1
    });
    return 4 === y0DayOfWeek || 3 === y0DayOfWeek && computeIsoInLeapYear(year) ? 53 : 52;
  }

  function computeGregoryEraFields({year: year}) {
    return year < 1 ? {
      era: "bce",
      eraYear: 1 - year
    } : {
      era: "ce",
      eraYear: year
    };
  }

  function validateIsoDateTimeFields(isoDateTime) {
    return validateIsoDateFields(isoDateTime), validateTimeFields(isoDateTime);
  }

  function validateIsoDateFields(isoInternals) {
    return constrainIsoDateFields(isoInternals, 1), isoInternals;
  }

  function constrainIsoDateFields(isoDate, overflow) {
    const {year: year} = isoDate;
    const month = clampProp(isoDate, "month", 1, 12, overflow);
    return {
      year: year,
      month: month,
      day: clampProp(isoDate, "day", 1, computeIsoDaysInMonth(year, month), overflow)
    };
  }

  function computeCalendarDateFields(calendar, isoDate) {
    return calendar ? calendar.ie(isoDate) : isoDate;
  }

  function computeCalendarMonthCodeParts(calendar, year, month) {
    return calendar ? calendar.O(year, month) : computeIsoMonthCodeParts(month);
  }

  function computeCalendarEraFields(calendar, isoDate) {
    return 0 === calendar ? computeGregoryEraFields(isoDate) : calendar ? calendar.h(isoDate) : {};
  }

  function computeCalendarIsoFieldsFromParts(calendar, year, month, day) {
    return calendar ? calendar.je(year, month, day) : computeIsoFieldsFromParts(year, month, day);
  }

  function computeCalendarMonthsInYearForYear(calendar, year) {
    return calendar ? calendar.k(year) : 12;
  }

  function computeCalendarDaysInMonthForYearMonth(calendar, year, month) {
    return calendar ? calendar.p(year, month) : computeIsoDaysInMonth(year, month);
  }

  function computeCalendarMonthCode(calendar, isoDate) {
    const {year: year, month: month} = computeCalendarDateFields(calendar, isoDate);
    const [monthCodeNumber, isLeapMonth] = computeCalendarMonthCodeParts(calendar, year, month);
    return formatMonthCode(monthCodeNumber, isLeapMonth);
  }

  function computeCalendarInLeapYear(calendar, isoDate) {
    const {year: year} = computeCalendarDateFields(calendar, isoDate);
    return calendar ? calendar.u(year) : computeIsoInLeapYear(year);
  }

  function computeCalendarMonthsInYear(calendar, isoDate) {
    const {year: year} = computeCalendarDateFields(calendar, isoDate);
    return computeCalendarMonthsInYearForYear(calendar, year);
  }

  function computeCalendarDaysInMonth(calendar, isoDate) {
    const {year: year, month: month} = computeCalendarDateFields(calendar, isoDate);
    return computeCalendarDaysInMonthForYearMonth(calendar, year, month);
  }

  function computeCalendarDaysInYear(calendar, isoDate) {
    const {year: year} = computeCalendarDateFields(calendar, isoDate);
    return calendar ? calendar.j(year) : computeIsoDaysInYear(year);
  }

  function computeCalendarDayOfYear(calendar, isoDate) {
    if (!calendar) {
      return computeIsoDayOfYear(isoDate);
    }
    const {year: year} = computeCalendarDateFields(calendar, isoDate);
    const yearStartIsoDate = computeCalendarIsoFieldsFromParts(calendar, year, 1, 1);
    return isoDateToEpochDays(isoDate) - isoDateToEpochDays(yearStartIsoDate) + 1;
  }

  function computeCalendarWeekOfYear(calendar, isoDate) {
    return calendar === isoCalendarImpl ? computeIsoWeekFields(isoDate).weekOfYear : void 0;
  }

  function computeCalendarYearOfWeek(calendar, isoDate) {
    return calendar === isoCalendarImpl ? computeIsoWeekFields(isoDate).yearOfWeek : void 0;
  }

  const requireString = /*@__PURE__*/ bindArgs(requireType, "string");

  function requireType(typeName, arg, entityName = typeName) {
    return typeof arg !== typeName && throwTypeError(invalidEntity(entityName, arg)), 
    arg;
  }

  function requireNumberIsInteger(num, entityName = "number") {
    return Number.isInteger(num) || throwRangeError(((entityName, num) => `Non-integer ${entityName}: ${num}`)(entityName, num)), 
    num || 0;
  }

  function toString$3(arg) {
    return "symbol" == typeof arg && throwTypeError("Cannot convert Symbol to string"), 
    String(arg);
  }

  function toStrictInteger(arg, entityName) {
    return requireNumberIsInteger(toFiniteNumber(arg, entityName), entityName);
  }

  const epochDisambigMap = {
    compatible: 0,
    reject: 1,
    earlier: 2,
    later: 3
  };

  const roundingModeFuncs = [ Math.floor, num => hasHalf(num) ? Math.floor(num) : Math.round(num), Math.ceil, num => hasHalf(num) ? Math.ceil(num) : Math.round(num), Math.trunc, num => hasHalf(num) ? Math.trunc(num) || 0 : Math.round(num), num => num < 0 ? Math.floor(num) : Math.ceil(num), num => Math.sign(num) * Math.round(Math.abs(num)) || 0, num => hasHalf(num) ? (num = Math.trunc(num) || 0) + num % 2 : Math.round(num) ];

  function coerceChoiceOption(optionName, enumNameMap, options, defaultChoice = 0) {
    const enumArg = options[optionName];
    if (void 0 === enumArg) {
      return defaultChoice;
    }
    const enumStr = toString$3(enumArg);
    const enumNum = enumNameMap[enumStr];
    return void 0 === enumNum && throwRangeError(invalidChoice(optionName, enumStr, enumNameMap)), 
    enumNum;
  }

  const coerceEpochDisambig = /*@__PURE__*/ bindArgs(coerceChoiceOption, "disambiguation", epochDisambigMap);

  const epochNanoMax = /*@__PURE__*/ BigInt(1e8) * bigNanoInUtcDay;

  const epochNanoMin = /*@__PURE__*/ BigInt(-1e8) * bigNanoInUtcDay;

  const plainDateEpochNanoMin = epochNanoMin - bigNanoInUtcDay;

  function checkIsoDateTimeInBounds(isoDateTime) {
    const epochNano = isoDateToEpochNano(isoDateTime);
    return checkIsoDateEpochNanoInBounds(epochNano), epochNano !== plainDateEpochNanoMin || timeFieldsToNano(isoDateTime) || throwRangeError(outOfBoundsDate), 
    isoDateTime;
  }

  function checkIsoDateEpochNanoInBounds(epochNano, allowPlainDateLowerEdge = 1) {
    (epochNano < (allowPlainDateLowerEdge ? plainDateEpochNanoMin : epochNanoMin) || epochNano > epochNanoMax) && throwRangeError(outOfBoundsDate);
  }

  function checkEpochNanoInBounds(epochNano) {
    return (epochNano < epochNanoMin || epochNano > epochNanoMax) && throwRangeError(outOfBoundsDate), 
    epochNano;
  }

  function isoDateTimeAndOffsetToEpochNano(isoDateTime, offsetNano) {
    return checkEpochNanoInBounds(isoDateToEpochNano(isoDateTime) + BigInt(timeFieldsToNano(isoDateTime) - offsetNano));
  }

  function createEpochNanoSlots(epochNano) {
    return {
      epochNanoseconds: epochNano
    };
  }

  function createZonedEpochNanoSlots(epochNano, timeZone, calendar) {
    return {
      calendar: calendar,
      timeZone: timeZone,
      epochNanoseconds: epochNano
    };
  }

  function createDateTimeSlots(isoDateTime, calendar) {
    return pluckProps(timeFieldNamesAsc, isoDateTime, createDateSlots(isoDateTime, calendar));
  }

  function createDateSlots(isoDate, calendar) {
    return pluckProps(calendarDateFieldNamesAsc, isoDate, {
      calendar: calendar
    });
  }

  function getEpochMilli(slots) {
    return epochNano = slots.epochNanoseconds, Number(divFloorBigInt(epochNano, bigNanoInMilli));
    var epochNano;
  }

  function getEpochNano(slots) {
    return slots.epochNanoseconds;
  }

  function roundToMinute$4(offsetNano) {
    return roundNumberToInc(offsetNano, nanoInMinute, 7);
  }

  function roundNumberToInc(num, roundingInc, roundingMode) {
    return roundWithMode(num / roundingInc, roundingMode) * roundingInc;
  }

  function roundWithMode(num, roundingMode) {
    return roundingModeFuncs[roundingMode](num);
  }

  const zonedEpochSlotsToIso = /*@__PURE__*/ memoize$1(_zonedEpochSlotsToIso, WeakMap);

  function _zonedEpochSlotsToIso(slots) {
    const {epochNanoseconds: epochNanoseconds, timeZone: timeZone} = slots;
    const offsetNanoseconds = timeZone.C(epochNanoseconds);
    return {
      ...epochNanoToIsoDateTime(epochNanoseconds + BigInt(offsetNanoseconds)),
      offsetNanoseconds: offsetNanoseconds
    };
  }

  function getSingleInstantFor(timeZone, isoDateTime, disambig = 0, possibleEpochNanos = timeZone.R(isoDateTime)) {
    if (1 === possibleEpochNanos.length) {
      return possibleEpochNanos[0];
    }
    if (1 === disambig && throwRangeError("Ambiguous offset"), possibleEpochNanos.length) {
      return possibleEpochNanos[3 === disambig ? 1 : 0];
    }
    const zonedEpochNano = isoDateTimeToEpochNano(isoDateTime);
    const gapNano = ((timeZone, zonedEpochNano) => {
      const startOffsetNano = timeZone.C(zonedEpochNano - bigNanoInUtcDay);
      return (gapNano => (gapNano > nanoInUtcDay && throwRangeError("Out-of-bounds TimeZone gap"), 
      gapNano))(timeZone.C(zonedEpochNano + bigNanoInUtcDay) - startOffsetNano);
    })(timeZone, zonedEpochNano);
    const shiftedIsoDateTime = epochNanoToIsoDateTime(zonedEpochNano + BigInt(gapNano * (2 === disambig ? -1 : 1)));
    return (possibleEpochNanos = timeZone.R(shiftedIsoDateTime))[2 === disambig ? 0 : possibleEpochNanos.length - 1];
  }

  const offsetRegExp = /*@__PURE__*/ createRegExp("([+-])(\\d{2})(?::?(\\d{2})(?::?(\\d{2})(?:[.,](\\d{1,9}))?)?)?");

  function parseOffsetNanoMaybe(s, onlyHourMinute) {
    const parts = offsetRegExp.exec(s);
    if (parts && (s => (s => {
      "T" !== s[0] && "t" !== s[0] || (s = s.slice(1));
      const fractionIndex = s.search(/[.,]/);
      const main = fractionIndex < 0 ? s : s.slice(0, fractionIndex);
      const parts = main.split(":");
      return 1 === parts.length ? /^(?:\d{2}|\d{4}|\d{6})$/i.test(main) : (2 === parts.length || 3 === parts.length) && parts.every(part => 2 === part.length && /^\d{2}$/i.test(part));
    })(s.slice(1)))(parts[0])) {
      return ((parts, onlyHourMinute) => {
        const firstSubMinutePart = parts[4] || parts[5];
        onlyHourMinute && firstSubMinutePart && throwRangeError(invalidSubstring(firstSubMinutePart));
        const offsetNanoPos = parseInt0(parts[2]) * nanoInHour + parseInt0(parts[3]) * nanoInMinute + parseInt0(parts[4]) * nanoInSec + parseSubsecNano(parts[5] || "");
        return offsetNano = offsetNanoPos * parseSign(parts[1]), Math.abs(offsetNano) >= nanoInUtcDay && throwRangeError("Out-of-bounds offset"), 
        offsetNano;
        var offsetNano;
      })(parts, onlyHourMinute);
    }
  }

  const RawDateTimeFormat = Intl.DateTimeFormat;

  function formatEpochMilliToPartsRecord(intlFormat, epochMilli) {
    epochMilli < -864e13 && throwRangeError(outOfBoundsDate);
    const parts = intlFormat.formatToParts(epochMilli);
    const hash = {};
    for (const part of parts) {
      hash[part.type] = part.value;
    }
    return hash;
  }

  const timeZonePeriodDaysByName = {
    "El_Aaiun": 17,
    "Tucuman": 12,
    "Tirane": 11,
    "Riga": 10,
    "Simferopol": 9,
    "Vienna": 9,
    "Tunis": 8,
    "Boa_Vista": 6,
    "Fortaleza": 6,
    "Maceio": 6,
    "Noronha": 6,
    "Recife": 6,
    "Gaza": 6,
    "Hebron": 6,
    "DeNoronha": 6
  };

  const minPossibleTransitionSec = -388152e4;

  function formatInstantIsoAuto(instantSlots) {
    return formatIsoDateTimeFields(epochNanoToIsoDateTime(instantSlots.epochNanoseconds), void 0) + "Z";
  }

  function formatZonedDateTimeIsoAuto(zonedDateTimeSlots) {
    const calendar = zonedDateTimeSlots.calendar;
    const timeZone = zonedDateTimeSlots.timeZone;
    const offsetNano = timeZone.C(zonedDateTimeSlots.epochNanoseconds);
    return formatIsoDateTimeFields(epochNanoToIsoDateTime(zonedDateTimeSlots.epochNanoseconds + BigInt(offsetNano)), void 0) + formatOffsetNano(roundToMinute$4(offsetNano)) + formatTimeZone(timeZone.id, 0) + (calendar === isoCalendarImpl ? "" : formatCalendarId(getCalendarSlotId(calendar), 0));
  }

  function formatDateTimeIsoAuto(isoDateTimeSlots) {
    const calendar = isoDateTimeSlots.calendar;
    return formatIsoDateTimeFields(isoDateTimeSlots, void 0) + (calendar === isoCalendarImpl ? "" : formatCalendarId(getCalendarSlotId(calendar), 0));
  }

  function formatIsoDateTimeFields(isoDateTime, subsecDigits) {
    return formatIsoDateFields(isoDateTime) + "T" + formatTimeFields(isoDateTime, subsecDigits);
  }

  function formatIsoDateFields(isoDateFields) {
    return formatIsoYearMonthFields(isoDateFields) + "-" + padNumber2(isoDateFields.day);
  }

  function formatIsoYearMonthFields(isoDateFields) {
    const {year: year} = isoDateFields;
    return (year < 0 || year > 9999 ? getSignStr(year) + padNumber(6, Math.abs(year)) : padNumber(4, year)) + "-" + padNumber2(isoDateFields.month);
  }

  function formatTimeFields(timeFields, subsecDigits) {
    const parts = [ padNumber2(timeFields.hour), padNumber2(timeFields.minute) ];
    return -1 !== subsecDigits && parts.push(padNumber2(timeFields.second) + ((millisecond, microsecond, nanosecond, subsecDigits) => formatSubsecNano(millisecond * nanoInMilli + microsecond * nanoInMicro + nanosecond, subsecDigits))(timeFields.millisecond, timeFields.microsecond, timeFields.nanosecond, subsecDigits)), 
    parts.join(":");
  }

  function formatOffsetNano(offsetNano, offsetDisplay = 0) {
    if (1 === offsetDisplay) {
      return "";
    }
    const [hour, nanoRemainder0] = divModFloor(Math.abs(offsetNano), nanoInHour);
    const [minute, nanoRemainder1] = divModFloor(nanoRemainder0, nanoInMinute);
    const [second, nanoRemainder2] = divModFloor(nanoRemainder1, nanoInSec);
    return getSignStr(offsetNano) + padNumber2(hour) + ":" + padNumber2(minute) + (second || nanoRemainder2 ? ":" + padNumber2(second) + formatSubsecNano(nanoRemainder2) : "");
  }

  function formatTimeZone(timeZoneId, timeZoneDisplay) {
    return 1 !== timeZoneDisplay ? "[" + (2 === timeZoneDisplay ? "!" : "") + timeZoneId + "]" : "";
  }

  function formatCalendarId(calendarId, isCritical) {
    return "[" + (isCritical ? "!" : "") + "u-ca=" + calendarId + "]";
  }

  const trailingZerosRE = /0+$/;

  function formatSubsecNano(totalNano, subsecDigits) {
    let s = padNumber(9, totalNano);
    return s = void 0 === subsecDigits ? s.replace(trailingZerosRE, "") : s.slice(0, subsecDigits), 
    s ? "." + s : "";
  }

  function getSignStr(num) {
    return num < 0 ? "-" : "+";
  }

  const icuRegExp = /^(AC|AE|AG|AR|AS|BE|BS|CA|CN|CS|CT|EA|EC|IE|IS|JS|MI|NE|NS|PL|PN|PR|PS|SS|VS)T$/;

  const badCharactersRegExp = /[^\w\/:+-]+/;

  function refineTimeZoneId(rawId) {
    return resolveTimeZoneId(requireString(rawId));
  }

  function resolveTimeZoneId(rawId) {
    return resolveTimeZoneRecord(rawId).id;
  }

  function resolveTimeZoneRecord(rawId) {
    const upperRawId = rawId.toUpperCase();
    const offsetRecord = (upperRawId => {
      const offsetNano = parseOffsetNanoMaybe(upperRawId, 1);
      if (void 0 !== offsetNano) {
        return {
          id: formatOffsetNano(offsetNano),
          _: offsetNano,
          o: offsetNano
        };
      }
    })(upperRawId);
    if (offsetRecord) {
      return {
        kind: "fixed",
        ...offsetRecord
      };
    }
    const normId = "UTC" === upperRawId ? "UTC" : (rawId => (badCharactersRegExp.test(rawId) && throwRangeError(invalidTimeZone(rawId)), 
    icuRegExp.test(rawId) && throwRangeError("Forbidden ICU TimeZone"), rawId.toLowerCase().split("/").map((part, partI) => (part.length <= 3 || /\d/.test(part)) && !/etc|yap/.test(part) ? part.toUpperCase() : part.replace(/baja|dumont|[a-z]+/g, (a, i) => a.length <= 2 && !partI || "in" === a || "chat" === a ? a.toUpperCase() : a.length > 2 || !i ? capitalize(a).replace(/island|noronha|murdo|rivadavia|urville/, capitalize) : a)).join("/")))(rawId);
    return queryNamedTimeZoneRecord(normId);
  }

  const queryNamedTimeZoneRecord = /*@__PURE__*/ memoize$1(normId => {
    if ("UTC" === normId) {
      return {
        kind: "utc",
        id: normId,
        o: normId
      };
    }
    const upperNormId = normId.toUpperCase();
    const format = queryTimeZoneIntlFormat(upperNormId);
    return {
      kind: "named",
      id: normId,
      format: format,
      o: format.resolvedOptions().timeZone
    };
  });

  const queryTimeZoneIntlFormat = /*@__PURE__*/ memoize$1(upperNormId => new RawDateTimeFormat("en-u-hc-h23", {
    calendar: "iso8601",
    timeZone: upperNormId,
    era: "short",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    second: "numeric"
  }));

  function queryTimeZone(rawTimeZoneId) {
    const record = resolveTimeZoneRecord(rawTimeZoneId);
    return queryTimeZoneRecord(record.id, record);
  }

  const queryTimeZoneRecord = /*@__PURE__*/ memoize$1((normTimeZoneId, record) => "named" === record.kind ? new IntlTimeZone(normTimeZoneId, record.o, record.format) : new FixedTimeZone(normTimeZoneId, record.o, "fixed" === record.kind ? record._ : 0));

  class FixedTimeZone {
    constructor(id, compareKey, offsetNano) {
      this.id = id, this.o = compareKey, this._ = offsetNano;
    }
    C() {
      return this._;
    }
    R(isoDateTime) {
      return [ isoDateTimeAndOffsetToEpochNano(isoDateTime, this._) ];
    }
    U() {}
  }

  class IntlTimeZone {
    constructor(id, compareKey, format) {
      this.id = id, this.o = compareKey, this.qe = ((computeOffsetSec, periodDays) => {
        const getSample = memoize$1(computeOffsetSec);
        const getSplit = memoize$1(createSplitTuple);
        const periodSec = 86400 * periodDays;
        function getOffsetSec(epochSec) {
          const [startEpochSec, endEpochSec] = computePeriod(epochSec, periodSec);
          const clampedStartEpochSec = clampIntlSampleEpochSec(startEpochSec);
          const clampedEndEpochSec = clampIntlSampleEpochSec(endEpochSec);
          const startOffsetSec = getSample(clampedStartEpochSec);
          const endOffsetSec = getSample(clampedEndEpochSec);
          return startOffsetSec === endOffsetSec ? startOffsetSec : pinch(getSplit(clampedStartEpochSec, clampedEndEpochSec), startOffsetSec, endOffsetSec, epochSec);
        }
        function pinch(split, startOffsetSec, endOffsetSec, forEpochSec) {
          let offsetSec;
          let splitDurSec;
          for (;(void 0 === forEpochSec || void 0 === (offsetSec = forEpochSec < split[0] ? startOffsetSec : forEpochSec >= split[1] ? endOffsetSec : void 0)) && (splitDurSec = split[1] - split[0]); ) {
            const middleEpochSec = split[0] + Math.floor(splitDurSec / 2);
            computeOffsetSec(middleEpochSec) === endOffsetSec ? split[1] = middleEpochSec : split[0] = middleEpochSec + 1;
          }
          return offsetSec;
        }
        return {
          Ee(zonedEpochSec) {
            const wideOffsetSec0 = getOffsetSec(zonedEpochSec - 86400);
            const wideOffsetSec1 = getOffsetSec(zonedEpochSec + 86400);
            const wideUtcEpochSec0 = zonedEpochSec - wideOffsetSec0;
            const wideUtcEpochSec1 = zonedEpochSec - wideOffsetSec1;
            if (wideOffsetSec0 === wideOffsetSec1) {
              return [ wideUtcEpochSec0 ];
            }
            const narrowOffsetSec0 = getOffsetSec(wideUtcEpochSec0);
            return narrowOffsetSec0 === getOffsetSec(wideUtcEpochSec1) ? [ zonedEpochSec - narrowOffsetSec0 ] : wideOffsetSec0 > wideOffsetSec1 ? [ wideUtcEpochSec0, wideUtcEpochSec1 ] : [];
          },
          De: getOffsetSec,
          U: function getTransition(epochSec, direction) {
            if (direction > 0 && epochSec >= 864e10) {
              return;
            }
            if (direction < 0) {
              if (epochSec <= minPossibleTransitionSec) {
                return;
              }
              const lookaheadEpochSec = getCurrentEpochSec() + 94867200;
              if (epochSec > lookaheadEpochSec) {
                return getTransition(lookaheadEpochSec, -1);
              }
            }
            const searchEpochSec = direction > 0 ? Math.max(epochSec, minPossibleTransitionSec) : epochSec;
            let [startEpochSec, endEpochSec] = computePeriod(searchEpochSec, periodSec);
            const inc = periodSec * direction;
            const searchLimit = direction > 0 ? Math.max(epochSec, getCurrentEpochSec()) + 94867200 : minPossibleTransitionSec;
            const inBounds = () => direction < 0 ? endEpochSec > searchLimit : startEpochSec < searchLimit;
            for (;inBounds(); ) {
              const clampedStartEpochSec = clampIntlSampleEpochSec(startEpochSec);
              const clampedEndEpochSec = clampIntlSampleEpochSec(endEpochSec);
              const startOffsetSec = getSample(clampedStartEpochSec);
              const endOffsetSec = getSample(clampedEndEpochSec);
              if (startOffsetSec !== endOffsetSec) {
                const split = getSplit(clampedStartEpochSec, clampedEndEpochSec);
                pinch(split, startOffsetSec, endOffsetSec);
                const transitionEpochSec = split[0];
                if ((compareNumbers$1(transitionEpochSec, epochSec) || 1) === direction) {
                  return transitionEpochSec;
                }
              }
              startEpochSec += inc, endEpochSec += inc;
            }
          }
        };
      })((format => epochSec => {
        const intlParts = formatEpochMilliToPartsRecord(format, 1e3 * epochSec);
        return 86400 * isoArgsToEpochDays((intlParts => {
          const relatedYear = intlParts.relatedYear;
          if (void 0 !== relatedYear) {
            return parseInt(relatedYear);
          }
          const year = parseInt(intlParts.year);
          return void 0 !== intlParts.era && "bce" === normalizeEraName(intlParts.era) ? 1 - year : year;
        })(intlParts), parseInt(intlParts.month), parseInt(intlParts.day)) + 3600 * parseInt(intlParts.hour) + 60 * parseInt(intlParts.minute) + parseInt(intlParts.second) - epochSec;
      })(format), (timeZoneId => {
        const timeZoneName = timeZoneId.split("/").pop();
        return timeZonePeriodDaysByName[timeZoneName] || 60;
      })(id));
    }
    C(epochNano) {
      return this.qe.De((epochNano => epochNanoToSecMod(epochNano)[0])(epochNano)) * nanoInSec;
    }
    R(isoDateTime) {
      const zonedEpochSec = 86400 * isoDateToEpochDays(isoDateTime) + timeFieldsToSec(isoDateTime);
      const subsecNano = timeFieldsToSubsecNano(isoDateTime);
      return this.qe.Ee(zonedEpochSec).map(epochSec => checkEpochNanoInBounds(BigInt(epochSec) * bigNanoInSec + BigInt(subsecNano)));
    }
    U(epochNano, direction) {
      const [epochSec, subsecNano] = epochNanoToSecMod(epochNano);
      const resEpochSec = this.qe.U(epochSec + (direction > 0 || subsecNano ? 1 : 0), direction);
      if (void 0 !== resEpochSec) {
        return BigInt(resEpochSec) * bigNanoInSec;
      }
    }
  }

  function getCurrentEpochSec() {
    return Math.floor(Date.now() / 1e3);
  }

  function createSplitTuple(startEpochSec, endEpochSec) {
    return [ startEpochSec, endEpochSec ];
  }

  function computePeriod(epochSec, periodSec) {
    const startEpochSec = Math.floor(epochSec / periodSec) * periodSec;
    return [ startEpochSec, startEpochSec + periodSec ];
  }

  function clampIntlSampleEpochSec(epochSec) {
    return constrainToRange(epochSec, -1e10, 864e10);
  }

  function instantToZonedDateTime(instantSlots, timeZone, calendar) {
    return createZonedEpochNanoSlots(instantSlots.epochNanoseconds, timeZone, calendar);
  }

  function plainDateTimeToZonedDateTime(plainDateTimeSlots, timeZone, options) {
    const epochNano = ((timeZone, isoDateTime, options) => {
      const epochDisambig = (options => coerceEpochDisambig(normalizeOptions(options)))(options);
      return getSingleInstantFor(timeZone, isoDateTime, epochDisambig);
    })(timeZone, plainDateTimeSlots, options);
    return createZonedEpochNanoSlots(checkEpochNanoInBounds(epochNano), timeZone, plainDateTimeSlots.calendar);
  }

  function epochMilliToInstant(epochMilli) {
    return createEpochNanoSlots(checkEpochNanoInBounds(BigInt(toStrictInteger(epochMilli)) * bigNanoInMilli));
  }

  const PlainDateTimeBranding = "PlainDateTime";

  const ZonedDateTimeBranding = "ZonedDateTime";

  const InstantBranding = "Instant";

  function defineTemporalClass(branding, cls, getSlots, ...getterMaps) {
    Object.defineProperties(cls, createNameDescriptors(branding)), Object.defineProperties(cls.prototype, createStringTagDescriptors("Temporal." + branding));
    for (const getterMap of getterMaps) {
      defineSlotGetters(cls.prototype, getSlots, getterMap);
    }
    return cls;
  }

  function defineSlotGetters(destPrototype, getSlots, getterMap) {
    Object.defineProperties(destPrototype, mapProps(getter => ({
      get() {
        return getter(getSlots(this));
      },
      configurable: 1
    }), getterMap));
  }

  const attachDebugString = "noop" === noop.name ? instance => {
    Object.defineProperty(instance, "_str_", {
      value: instance.toJSON()
    });
  } : noop;

  function invalidRecordType() {
    throwTypeError(invalidCallingContext);
  }

  function forbiddenValueOf() {
    throwTypeError(forbiddenValueOf$1);
  }

  const dateFieldGetters$1 = {
    era(slots) {
      return computeCalendarEraFields(slots.calendar, slots).era;
    },
    eraYear(slots) {
      return computeCalendarEraFields(slots.calendar, slots).eraYear;
    },
    year(slots) {
      return computeCalendarDateFields(slots.calendar, slots).year;
    },
    month(slots) {
      return computeCalendarDateFields(slots.calendar, slots).month;
    },
    monthCode(slots) {
      return computeCalendarMonthCode(slots.calendar, slots);
    },
    day(slots) {
      return computeCalendarDateFields(slots.calendar, slots).day;
    }
  };

  const yearMonthDerivedGetters = {
    daysInMonth(slots) {
      return computeCalendarDaysInMonth(slots.calendar, slots);
    },
    daysInYear(slots) {
      return computeCalendarDaysInYear(slots.calendar, slots);
    },
    monthsInYear(slots) {
      return computeCalendarMonthsInYear(slots.calendar, slots);
    },
    inLeapYear(slots) {
      return computeCalendarInLeapYear(slots.calendar, slots);
    }
  };

  const dateDerivedGetters = {
    dayOfWeek(slots) {
      return computeIsoDayOfWeek(slots);
    },
    dayOfYear(slots) {
      return computeCalendarDayOfYear(slots.calendar, slots);
    },
    weekOfYear(slots) {
      return computeCalendarWeekOfYear(slots.calendar, slots);
    },
    yearOfWeek(slots) {
      return computeCalendarYearOfWeek(slots.calendar, slots);
    },
    daysInWeek() {
      return 7;
    },
    daysInMonth(slots) {
      return computeCalendarDaysInMonth(slots.calendar, slots);
    },
    daysInYear(slots) {
      return computeCalendarDaysInYear(slots.calendar, slots);
    },
    monthsInYear(slots) {
      return computeCalendarMonthsInYear(slots.calendar, slots);
    },
    inLeapYear(slots) {
      return computeCalendarInLeapYear(slots.calendar, slots);
    }
  };

  function createNativeGetters(shimGetters) {
    return createPropGetters(Object.keys(shimGetters));
  }

  const timeGetters = /*@__PURE__*/ createNativeGetters(timeGetters$1);

  const dateFieldGetters = /*@__PURE__*/ createNativeGetters(dateFieldGetters$1);

  createNativeGetters(yearMonthDerivedGetters), createNativeGetters(dateDerivedGetters);

  const PlainDateTimeRecordBranding = `${PlainDateTimeBranding}Record`;

  const ZonedDateTimeRecordBranding = `${ZonedDateTimeBranding}Record`;

  const InstantRecordBranding = `${InstantBranding}Record`;

  const calendarMap = /*@__PURE__*/ new WeakMap;

  const instantMap = /*@__PURE__*/ new WeakMap;

  const zonedDateTimeMap = /*@__PURE__*/ new WeakMap;

  const plainDateTimeMap = /*@__PURE__*/ new WeakMap;

  function getCalendarSlots(record) {
    return getCalendarSlotsIfPresent(record) || invalidRecordType();
  }

  function getCalendarSlotsIfPresent(record) {
    return calendarMap.get(record);
  }

  function getInstantSlots(record) {
    return getInstantSlotsIfPresent(record) || invalidRecordType();
  }

  function getInstantSlotsIfPresent(record) {
    return instantMap.get(record);
  }

  function setInstantSlots(instance, slots) {
    instantMap.set(instance, slots);
  }

  function getZonedDateTimeSlots(record) {
    return getZonedDateTimeSlotsIfPresent(record) || invalidRecordType();
  }

  function getZonedDateTimeSlotsIfPresent(record) {
    return zonedDateTimeMap.get(record);
  }

  function setZonedDateTimeSlots(instance, slots) {
    zonedDateTimeMap.set(instance, slots);
  }

  function getPlainDateTimeSlots(record) {
    return getPlainDateTimeSlotsIfPresent(record) || invalidRecordType();
  }

  function getPlainDateTimeSlotsIfPresent(record) {
    return plainDateTimeMap.get(record);
  }

  function setPlainDateTimeSlots(instance, slots) {
    plainDateTimeMap.set(instance, slots);
  }

  function getCalendarRecordId(record) {
    return getCalendarSlots(record).id;
  }

  function getCalendarRecordImplCreator(record) {
    const getImpl = getCalendarSlots(record).Be;
    return getImpl || throwRangeError(exoticCalendarRequired(getCalendarRecordId(record), "getExotic or getAny")), 
    getImpl;
  }

  function refineNativeCalendarArgMaybe(calendarRecord) {
    if (void 0 !== calendarRecord) {
      return getValidatedCalendarId(calendarRecord);
    }
  }

  function getValidatedCalendarId(record) {
    return getCalendarRecordImplCreator(record), getCalendarRecordId(record);
  }

  const getNativePlainDateTime = getPlainDateTimeSlots;

  const NativePlainDateTimeRecord = /*@__PURE__*/ defineTemporalClass(PlainDateTimeRecordBranding, class {
    get calendarId() {
      return getNativePlainDateTime(this).calendarId;
    }
    toJSON() {
      return getNativePlainDateTime(this).toJSON();
    }
    valueOf() {
      return getNativePlainDateTime(this).valueOf();
    }
  }, getNativePlainDateTime, dateFieldGetters, timeGetters);

  function createNativePlainDateTimeRecord(native) {
    const instance = Object.create(NativePlainDateTimeRecord.prototype);
    return setPlainDateTimeSlots(instance, native), attachDebugString(instance), instance;
  }

  function create$5$1(isoYear, isoMonth, isoDay, hour, minute, second, millisecond, microsecond, nanosecond, calendar) {
    return createNativePlainDateTimeRecord(new NativeTemporal.PlainDateTime(isoYear, isoMonth, isoDay, hour, minute, second, millisecond, microsecond, nanosecond, refineNativeCalendarArgMaybe(calendar)));
  }

  function toZonedDateTime$1$1(record, timeZoneId, options) {
    return createNativeZonedDateTimeRecord(getNativePlainDateTime(record).toZonedDateTime(timeZoneId, options));
  }

  const getNativeZonedDateTime = getZonedDateTimeSlots;

  const NativeZonedDateTimeRecord = /*@__PURE__*/ defineTemporalClass(ZonedDateTimeRecordBranding, class {
    get calendarId() {
      return getNativeZonedDateTime(this).calendarId;
    }
    get timeZoneId() {
      return getNativeZonedDateTime(this).timeZoneId;
    }
    get epochMilliseconds() {
      return getNativeZonedDateTime(this).epochMilliseconds;
    }
    get epochNanoseconds() {
      return getNativeZonedDateTime(this).epochNanoseconds;
    }
    toJSON() {
      return getNativeZonedDateTime(this).toJSON();
    }
    valueOf() {
      return getNativeZonedDateTime(this).valueOf();
    }
  }, getNativeZonedDateTime, dateFieldGetters, timeGetters);

  function createNativeZonedDateTimeRecord(native) {
    const instance = Object.create(NativeZonedDateTimeRecord.prototype);
    return setZonedDateTimeSlots(instance, native), attachDebugString(instance), instance;
  }

  function offsetNanoseconds$2(record) {
    return getNativeZonedDateTime(record).offsetNanoseconds;
  }

  const getNativeInstant = getInstantSlots;

  const NativeInstantRecord = /*@__PURE__*/ defineTemporalClass(InstantRecordBranding, class {
    get epochMilliseconds() {
      return getNativeInstant(this).epochMilliseconds;
    }
    get epochNanoseconds() {
      return getNativeInstant(this).epochNanoseconds;
    }
    toJSON() {
      return getNativeInstant(this).toJSON();
    }
    valueOf() {
      return getNativeInstant(this).valueOf();
    }
  });

  function createNativeInstantRecord(native) {
    const instance = Object.create(NativeInstantRecord.prototype);
    return setInstantSlots(instance, native), attachDebugString(instance), instance;
  }

  function fromEpochMilliseconds$2(epochMilliseconds) {
    return createNativeInstantRecord(NativeTemporal.Instant.fromEpochMilliseconds(epochMilliseconds));
  }

  function toZonedDateTimeISO$2(record, timeZoneId) {
    return createNativeZonedDateTimeRecord(getNativeInstant(record).toZonedDateTimeISO(timeZoneId));
  }

  function refineShimCalendarArgMaybe(calendarRecord) {
    return void 0 === calendarRecord ? isoCalendarImpl : getCalendarRecordImpl(calendarRecord);
  }

  function getCalendarRecordImpl(record) {
    return getCalendarRecordImplCreator(record)();
  }

  const getShimPlainDateTimeSlots = getPlainDateTimeSlots;

  const ShimPlainDateTimeRecord = /*@__PURE__*/ defineTemporalClass(PlainDateTimeRecordBranding, class {
    get calendarId() {
      return getCalendarSlotId(getShimPlainDateTimeSlots(this).calendar);
    }
    toJSON() {
      return formatDateTimeIsoAuto(getShimPlainDateTimeSlots(this));
    }
    valueOf() {
      return forbiddenValueOf();
    }
  }, getShimPlainDateTimeSlots, dateFieldGetters$1, timeGetters$1);

  function createShimPlainDateTimeRecord(slots) {
    const instance = Object.create(ShimPlainDateTimeRecord.prototype);
    return setPlainDateTimeSlots(instance, slots), attachDebugString(instance), instance;
  }

  function create$5(isoYear, isoMonth, isoDay, hour = 0, minute = 0, second = 0, millisecond = 0, microsecond = 0, nanosecond = 0, calendar) {
    const fields = checkIsoDateTimeInBounds(validateIsoDateTimeFields(mapProps(toIntegerWithTrunc, {
      year: isoYear,
      month: isoMonth,
      day: isoDay,
      hour: hour,
      minute: minute,
      second: second,
      millisecond: millisecond,
      microsecond: microsecond,
      nanosecond: nanosecond
    })));
    const calendarImpl = refineShimCalendarArgMaybe(calendar);
    return createShimPlainDateTimeRecord(createDateTimeSlots(fields, calendarImpl));
  }

  function toZonedDateTime$1(record, timeZoneId, options) {
    return createShimZonedDateTimeRecord(plainDateTimeToZonedDateTime(getShimPlainDateTimeSlots(record), queryTimeZone(refineTimeZoneId(timeZoneId)), options));
  }

  const getShimZonedDateTimeSlots = getZonedDateTimeSlots;

  const ShimZonedDateTimeRecord = /*@__PURE__*/ defineTemporalClass(ZonedDateTimeRecordBranding, class {
    get calendarId() {
      return getCalendarSlotId(getShimZonedDateTimeSlots(this).calendar);
    }
    get timeZoneId() {
      return getShimZonedDateTimeSlots(this).timeZone.id;
    }
    get epochMilliseconds() {
      return getEpochMilli(getShimZonedDateTimeSlots(this));
    }
    get epochNanoseconds() {
      return getEpochNano(getShimZonedDateTimeSlots(this));
    }
    toJSON() {
      return formatZonedDateTimeIsoAuto(getShimZonedDateTimeSlots(this));
    }
    valueOf() {
      return forbiddenValueOf();
    }
  }, getShimZonedDateTimeIsoSlots, dateFieldGetters$1, timeGetters$1);

  function createShimZonedDateTimeRecord(slots) {
    const instance = Object.create(ShimZonedDateTimeRecord.prototype);
    return setZonedDateTimeSlots(instance, slots), attachDebugString(instance), instance;
  }

  function getShimZonedDateTimeIsoSlots(record) {
    const slots = getShimZonedDateTimeSlots(record);
    return {
      ...zonedEpochSlotsToIso(slots),
      calendar: slots.calendar
    };
  }

  function offsetNanoseconds$1(record) {
    return zonedEpochSlotsToIso(getShimZonedDateTimeSlots(record)).offsetNanoseconds;
  }

  const getShimInstantSlots = getInstantSlots;

  const ShimInstantRecord = /*@__PURE__*/ defineTemporalClass(InstantRecordBranding, class {
    get epochMilliseconds() {
      return getEpochMilli(getShimInstantSlots(this));
    }
    get epochNanoseconds() {
      return getEpochNano(getShimInstantSlots(this));
    }
    toJSON() {
      return formatInstantIsoAuto(getShimInstantSlots(this));
    }
    valueOf() {
      return forbiddenValueOf();
    }
  });

  function createShimInstantRecord(slots) {
    const instance = Object.create(ShimInstantRecord.prototype);
    return setInstantSlots(instance, slots), attachDebugString(instance), instance;
  }

  function fromEpochMilliseconds$1(epochMilliseconds) {
    return createShimInstantRecord(epochMilliToInstant(epochMilliseconds));
  }

  function toZonedDateTimeISO$1(record, timeZoneId) {
    return createShimZonedDateTimeRecord(instantToZonedDateTime(getShimInstantSlots(record), queryTimeZone(refineTimeZoneId(timeZoneId))));
  }

  const offsetNanoseconds = NativeTemporal ? offsetNanoseconds$2 : offsetNanoseconds$1;

  const create = NativeTemporal ? create$5$1 : create$5;

  const toZonedDateTime = NativeTemporal ? toZonedDateTime$1$1 : toZonedDateTime$1;

  const fromEpochMilliseconds = NativeTemporal ? fromEpochMilliseconds$2 : fromEpochMilliseconds$1;

  const toZonedDateTimeISO = NativeTemporal ? toZonedDateTimeISO$2 : toZonedDateTimeISO$1;

  // Adding
  function addWeeks(m, n) {
      let a = dateToUtcArray(m);
      a[2] += n * 7;
      return arrayToUtcDate(a);
  }
  function addDays(m, n) {
      let a = dateToUtcArray(m);
      a[2] += n;
      return arrayToUtcDate(a);
  }
  function addMs(m, n) {
      let a = dateToUtcArray(m);
      a[6] += n;
      return arrayToUtcDate(a);
  }
  // Diffing (all return floats)
  // TODO: why not use ranges?
  function diffWeeks(m0, m1) {
      return diffDays(m0, m1) / 7;
  }
  function diffDays(m0, m1) {
      return (m1.valueOf() - m0.valueOf()) / (1000 * 60 * 60 * 24);
  }
  function diffHours(m0, m1) {
      return (m1.valueOf() - m0.valueOf()) / (1000 * 60 * 60);
  }
  function diffMinutes(m0, m1) {
      return (m1.valueOf() - m0.valueOf()) / (1000 * 60);
  }
  function diffSeconds(m0, m1) {
      return (m1.valueOf() - m0.valueOf()) / 1000;
  }
  function diffDayAndTime(m0, m1) {
      let m0day = startOfDay(m0);
      let m1day = startOfDay(m1);
      return {
          years: 0,
          months: 0,
          days: Math.round(diffDays(m0day, m1day)),
          milliseconds: (m1.valueOf() - m1day.valueOf()) - (m0.valueOf() - m0day.valueOf()),
      };
  }
  // Diffing Whole Units
  function diffWholeWeeks(m0, m1) {
      let d = diffWholeDays(m0, m1);
      if (d !== null && d % 7 === 0) {
          return d / 7;
      }
      return null;
  }
  function diffWholeDays(m0, m1) {
      if (timeAsMs(m0) === timeAsMs(m1)) {
          return Math.round(diffDays(m0, m1));
      }
      return null;
  }
  // Start-Of
  function startOfDay(m) {
      return arrayToUtcDate([
          m.getUTCFullYear(),
          m.getUTCMonth(),
          m.getUTCDate(),
      ]);
  }
  function startOfHour(m) {
      return arrayToUtcDate([
          m.getUTCFullYear(),
          m.getUTCMonth(),
          m.getUTCDate(),
          m.getUTCHours(),
      ]);
  }
  function startOfMinute(m) {
      return arrayToUtcDate([
          m.getUTCFullYear(),
          m.getUTCMonth(),
          m.getUTCDate(),
          m.getUTCHours(),
          m.getUTCMinutes(),
      ]);
  }
  function startOfSecond(m) {
      return arrayToUtcDate([
          m.getUTCFullYear(),
          m.getUTCMonth(),
          m.getUTCDate(),
          m.getUTCHours(),
          m.getUTCMinutes(),
          m.getUTCSeconds(),
      ]);
  }
  // Week Computation
  function weekOfYear(marker, dow, doy) {
      let y = marker.getUTCFullYear();
      let w = weekOfGivenYear(marker, y, dow, doy);
      if (w < 1) {
          return weekOfGivenYear(marker, y - 1, dow, doy);
      }
      let nextW = weekOfGivenYear(marker, y + 1, dow, doy);
      if (nextW >= 1) {
          return Math.min(w, nextW);
      }
      return w;
  }
  function weekOfGivenYear(marker, year, dow, doy) {
      let firstWeekStart = arrayToUtcDate([year, 0, 1 + firstWeekOffset(year, dow, doy)]);
      let dayStart = startOfDay(marker);
      let days = Math.round(diffDays(firstWeekStart, dayStart));
      return Math.floor(days / 7) + 1; // zero-indexed
  }
  // start-of-first-week - start-of-year
  function firstWeekOffset(year, dow, doy) {
      // first-week day -- which january is always in the first week (4 for iso, 1 for other)
      let fwd = 7 + dow - doy;
      // first-week day local weekday -- which local weekday is fwd
      let fwdlw = (7 + arrayToUtcDate([year, 0, fwd]).getUTCDay() - dow) % 7;
      return -fwdlw + fwd - 1;
  }
  // Array Conversion
  function dateToLocalArray(date) {
      return [
          date.getFullYear(),
          date.getMonth(),
          date.getDate(),
          date.getHours(),
          date.getMinutes(),
          date.getSeconds(),
          date.getMilliseconds(),
      ];
  }
  function arrayToLocalDate(a) {
      return new Date(a[0], a[1] || 0, a[2] == null ? 1 : a[2], // day of month
      a[3] || 0, a[4] || 0, a[5] || 0);
  }
  function dateToUtcArray(date) {
      return [
          date.getUTCFullYear(),
          date.getUTCMonth(),
          date.getUTCDate(),
          date.getUTCHours(),
          date.getUTCMinutes(),
          date.getUTCSeconds(),
          date.getUTCMilliseconds(),
      ];
  }
  function arrayToUtcDate(a) {
      // according to web standards (and Safari), a month index is required.
      // massage if only given a year.
      if (a.length === 1) {
          a = a.concat([0]);
      }
      return new Date(Date.UTC(...a));
  }
  // Other Utils
  function isValidDate(m) {
      return !isNaN(m.valueOf());
  }
  function timeAsMs(m) {
      return m.getUTCHours() * 1000 * 60 * 60 +
          m.getUTCMinutes() * 1000 * 60 +
          m.getUTCSeconds() * 1000 +
          m.getUTCMilliseconds();
  }

  let calendarSystemClassMap = {};
  function registerCalendarSystem(name, theClass) {
      calendarSystemClassMap[name] = theClass;
  }
  function createCalendarSystem(name) {
      return new calendarSystemClassMap[name]();
  }
  class GregorianCalendarSystem {
      getMarkerYear(d) {
          return d.getUTCFullYear();
      }
      getMarkerMonth(d) {
          return d.getUTCMonth();
      }
      getMarkerDay(d) {
          return d.getUTCDate();
      }
      arrayToMarker(arr) {
          return arrayToUtcDate(arr);
      }
      markerToArray(marker) {
          return dateToUtcArray(marker);
      }
  }
  registerCalendarSystem('gregory', GregorianCalendarSystem);

  function parseRange(input, dateEnv) {
      let start = null;
      let end = null;
      if (input.start) {
          start = dateEnv.createMarker(input.start);
      }
      if (input.end) {
          end = dateEnv.createMarker(input.end);
      }
      if (!start && !end) {
          return null;
      }
      if (start && end && end < start) {
          return null;
      }
      return { start, end };
  }
  // SIDE-EFFECT: will mutate ranges.
  // Will return a new array result.
  function invertRanges(ranges, constraintRange) {
      let invertedRanges = [];
      let { start } = constraintRange; // the end of the previous range. the start of the new range
      let i;
      let dateRange;
      // ranges need to be in order. required for our date-walking algorithm
      ranges.sort(compareRanges);
      for (i = 0; i < ranges.length; i += 1) {
          dateRange = ranges[i];
          // add the span of time before the event (if there is any)
          if (dateRange.start > start) { // compare millisecond time (skip any ambig logic)
              invertedRanges.push({ start, end: dateRange.start });
          }
          if (dateRange.end > start) {
              start = dateRange.end;
          }
      }
      // add the span of time after the last event (if there is any)
      if (start < constraintRange.end) { // compare millisecond time (skip any ambig logic)
          invertedRanges.push({ start, end: constraintRange.end });
      }
      return invertedRanges;
  }
  function compareRanges(range0, range1) {
      return range0.start.valueOf() - range1.start.valueOf(); // earlier ranges go first
  }
  function intersectRanges(range0, range1) {
      let { start, end } = range0;
      let newRange = null;
      if (range1.start !== null) {
          if (start === null) {
              start = range1.start;
          }
          else {
              start = new Date(Math.max(start.valueOf(), range1.start.valueOf()));
          }
      }
      if (range1.end != null) {
          if (end === null) {
              end = range1.end;
          }
          else {
              end = new Date(Math.min(end.valueOf(), range1.end.valueOf()));
          }
      }
      if (start === null || end === null || start < end) {
          newRange = { start, end };
      }
      return newRange;
  }
  function rangesEqual(range0, range1) {
      return (range0.start === null ? null : range0.start.valueOf()) === (range1.start === null ? null : range1.start.valueOf()) &&
          (range0.end === null ? null : range0.end.valueOf()) === (range1.end === null ? null : range1.end.valueOf());
  }
  function rangesIntersect(range0, range1) {
      return (range0.end === null || range1.start === null || range0.end > range1.start) &&
          (range0.start === null || range1.end === null || range0.start < range1.end);
  }
  function rangeContainsRange(outerRange, innerRange) {
      return (outerRange.start === null || (innerRange.start !== null && innerRange.start >= outerRange.start)) &&
          (outerRange.end === null || (innerRange.end !== null && innerRange.end <= outerRange.end));
  }
  function rangeContainsMarker(range, date) {
      return (range.start === null || date >= range.start) &&
          (range.end === null || date < range.end);
  }
  // If the given date is not within the given range, move it inside.
  // (If it's past the end, make it one millisecond before the end).
  function constrainMarkerToRange(date, range) {
      if (range.start != null && date < range.start) {
          return range.start;
      }
      if (range.end != null && date >= range.end) {
          return new Date(range.end.valueOf() - 1);
      }
      return date;
  }

  function expandZonedInstant(dateInfo, calendarSystem) {
      let a = calendarSystem.markerToArray(dateInfo.marker);
      return {
          marker: dateInfo.marker,
          instantMs: dateInfo.instantMs,
          timeZoneOffset: (dateInfo.marker.valueOf() - dateInfo.instantMs) / 60000,
          array: a,
          year: a[0],
          month: a[1],
          day: a[2],
          hour: a[3],
          minute: a[4],
          second: a[5],
          millisecond: a[6],
      };
  }
  function createVerboseFormattingArg(start, end, context) {
      let startInfo = expandZonedInstant(start, context.calendarSystem);
      let endInfo = end ? expandZonedInstant(end, context.calendarSystem) : null;
      return {
          date: startInfo,
          start: startInfo,
          end: endInfo,
          timeZone: context.timeZone,
          localeCodes: context.locale.codes,
      };
  }

  function isInt(n) {
      return n % 1 === 0;
  }
  function padStart(val, len) {
      let s = String(val);
      return '000'.substr(0, len - s.length) + s;
  }

  const INTERNAL_UNITS = ['years', 'months', 'days', 'milliseconds'];
  const PARSE_RE = /^(-?)(?:(\d+)\.)?(\d+):(\d\d)(?::(\d\d)(?:\.(\d\d\d))?)?/;
  // Parsing and Creation
  function createDuration(input, unit) {
      if (typeof input === 'string') {
          return parseString(input);
      }
      if (typeof input === 'object' && input) { // non-null object
          return parseObject(input);
      }
      if (typeof input === 'number') {
          return parseObject({ [unit || 'milliseconds']: input });
      }
      return null;
  }
  function parseString(s) {
      let m = PARSE_RE.exec(s);
      if (m) {
          let sign = m[1] ? -1 : 1;
          return {
              years: 0,
              months: 0,
              days: sign * (m[2] ? parseInt(m[2], 10) : 0),
              milliseconds: sign * ((m[3] ? parseInt(m[3], 10) : 0) * 60 * 60 * 1000 + // hours
                  (m[4] ? parseInt(m[4], 10) : 0) * 60 * 1000 + // minutes
                  (m[5] ? parseInt(m[5], 10) : 0) * 1000 + // seconds
                  (m[6] ? parseInt(m[6], 10) : 0) // ms
              ),
          };
      }
      return null;
  }
  function parseObject(obj) {
      let duration = {
          years: obj.years || obj.year || 0,
          months: obj.months || obj.month || 0,
          days: obj.days || obj.day || 0,
          milliseconds: (obj.hours || obj.hour || 0) * 60 * 60 * 1000 + // hours
              (obj.minutes || obj.minute || 0) * 60 * 1000 + // minutes
              (obj.seconds || obj.second || 0) * 1000 + // seconds
              (obj.milliseconds || obj.millisecond || obj.ms || 0), // ms
      };
      let weeks = obj.weeks || obj.week;
      if (weeks) {
          duration.days += weeks * 7;
          duration.specifiedWeeks = true;
      }
      return duration;
  }
  // Equality
  function durationsEqual(d0, d1) {
      return d0.years === d1.years &&
          d0.months === d1.months &&
          d0.days === d1.days &&
          d0.milliseconds === d1.milliseconds;
  }
  function asCleanDays(dur) {
      if (!dur.years && !dur.months && !dur.milliseconds) {
          return dur.days;
      }
      return 0;
  }
  // Simple Math
  function addDurations(d0, d1) {
      return {
          years: d0.years + d1.years,
          months: d0.months + d1.months,
          days: d0.days + d1.days,
          milliseconds: d0.milliseconds + d1.milliseconds,
      };
  }
  function subtractDurations(d1, d0) {
      return {
          years: d1.years - d0.years,
          months: d1.months - d0.months,
          days: d1.days - d0.days,
          milliseconds: d1.milliseconds - d0.milliseconds,
      };
  }
  function multiplyDuration(d, n) {
      return {
          years: d.years * n,
          months: d.months * n,
          days: d.days * n,
          milliseconds: d.milliseconds * n,
      };
  }
  // Conversions
  // "Rough" because they are based on average-case Gregorian months/years
  function asRoughYears(dur) {
      return asRoughDays(dur) / 365;
  }
  function asRoughMonths(dur) {
      return asRoughDays(dur) / 30;
  }
  function asRoughDays(dur) {
      return asRoughMs(dur) / 864e5;
  }
  function asRoughMinutes(dur) {
      return asRoughMs(dur) / (1000 * 60);
  }
  function asRoughSeconds(dur) {
      return asRoughMs(dur) / 1000;
  }
  function asRoughMs(dur) {
      return dur.years * (365 * 864e5) +
          dur.months * (30 * 864e5) +
          dur.days * 864e5 +
          dur.milliseconds;
  }
  // Advanced Math
  function wholeDivideDurations(numerator, denominator) {
      let res = null;
      for (let i = 0; i < INTERNAL_UNITS.length; i += 1) {
          let unit = INTERNAL_UNITS[i];
          if (denominator[unit]) {
              let localRes = numerator[unit] / denominator[unit];
              if (!isInt(localRes) || (res !== null && res !== localRes)) {
                  return null;
              }
              res = localRes;
          }
          else if (numerator[unit]) {
              // needs to divide by something but can't!
              return null;
          }
      }
      return res;
  }
  function greatestDurationDenominator(dur) {
      let ms = dur.milliseconds;
      if (ms) {
          if (ms % 1000 !== 0) {
              return { unit: 'millisecond', value: ms };
          }
          if (ms % (1000 * 60) !== 0) {
              return { unit: 'second', value: ms / 1000 };
          }
          if (ms % (1000 * 60 * 60) !== 0) {
              return { unit: 'minute', value: ms / (1000 * 60) };
          }
          if (ms) {
              return { unit: 'hour', value: ms / (1000 * 60 * 60) };
          }
      }
      if (dur.days) {
          if (dur.specifiedWeeks && dur.days % 7 === 0) {
              return { unit: 'week', value: dur.days / 7 };
          }
          return { unit: 'day', value: dur.days };
      }
      if (dur.months) {
          return { unit: 'month', value: dur.months };
      }
      if (dur.years) {
          return { unit: 'year', value: dur.years };
      }
      return { unit: 'millisecond', value: 0 };
  }

  // timeZoneOffset is in minutes
  function buildIsoString(marker, timeZoneOffset, stripZeroTime = false) {
      let s = marker.toISOString();
      s = s.replace('.000', '');
      if (stripZeroTime) {
          s = s.replace('T00:00:00Z', '');
      }
      if (s.length > 10) {
          if (timeZoneOffset == null) {
              s = s.replace('Z', '');
          }
          else if (timeZoneOffset !== 0) {
              s = s.replace('Z', formatTimeZoneOffset(timeZoneOffset, true));
          }
      }
      return s;
  }
  function formatDayString(marker) {
      return marker.toISOString().replace(/T.*$/, '');
  }
  function formatIsoMonthStr(marker) {
      return marker.toISOString().match(/^\d{4}-\d{2}/)[0];
  }
  function formatIsoTimeString(marker) {
      return padStart(marker.getUTCHours(), 2) + ':' +
          padStart(marker.getUTCMinutes(), 2) + ':' +
          padStart(marker.getUTCSeconds(), 2);
  }
  function formatTimeZoneOffset(minutes, doIso = false) {
      let sign = minutes < 0 ? '-' : '+';
      let abs = Math.abs(minutes);
      let hours = Math.floor(abs / 60);
      let mins = Math.round(abs % 60);
      if (doIso) {
          return `${sign + padStart(hours, 2)}:${padStart(mins, 2)}`;
      }
      return `GMT${sign}${hours}${mins ? `:${padStart(mins, 2)}` : ''}`;
  }
  function joinDateTimeFormatParts(parts) {
      let s = '';
      for (const part of parts) {
          s += part.value;
      }
      return s;
  }

  const ISO_RE = /^\s*(\d{4})(-?(\d{2})(-?(\d{2})([T ](\d{2}):?(\d{2})(:?(\d{2})(\.(\d+))?)?(Z|(([-+])(\d{2})(:?(\d{2}))?))?)?)?)?$/;
  function parse(str) {
      let m = ISO_RE.exec(str);
      if (m) {
          let marker = new Date(Date.UTC(Number(m[1]), m[3] ? Number(m[3]) - 1 : 0, Number(m[5] || 1), Number(m[7] || 0), Number(m[8] || 0), Number(m[10] || 0), m[12] ? Number(`0.${m[12]}`) * 1000 : 0));
          if (isValidDate(marker)) {
              let timeZoneOffset = null;
              if (m[13]) {
                  timeZoneOffset = (m[15] === '-' ? -1 : 1) * (Number(m[16] || 0) * 60 +
                      Number(m[18] || 0));
              }
              return {
                  marker,
                  isTimeUnspecified: !m[6],
                  timeZoneOffset,
              };
          }
      }
      return null;
  }

  class DateEnv {
      constructor(settings) {
          this.timeZone = settings.timeZone;
          this.calendarSystem = createCalendarSystem(settings.calendarSystem);
          this.locale = settings.locale;
          this.weekDow = settings.locale.week.dow;
          this.weekDoy = settings.locale.week.doy;
          if (settings.weekNumberCalculation === 'ISO') {
              this.weekDow = 1;
              this.weekDoy = 4;
          }
          if (typeof settings.firstDay === 'number') {
              this.weekDow = settings.firstDay;
          }
          if (typeof settings.weekNumberCalculation === 'function') {
              this.weekNumberFunc = settings.weekNumberCalculation;
          }
          this.weekTextLong = settings.weekTextLong;
          this.weekTextShort = settings.weekTextShort ?? settings.weekTextLong;
          this.cmdFormatter = settings.cmdFormatter;
      }
      // Creating / Parsing
      createMarker(input) {
          let meta = this.createMarkerMeta(input);
          if (meta === null) {
              return null;
          }
          return meta.marker;
      }
      createNowMarker() {
          return this.timestampToMarker(new Date().valueOf());
      }
      createMarkerMeta(input) {
          if (typeof input === 'string') {
              return this.parse(input);
          }
          let marker = null;
          let instantMs;
          if (typeof input === 'number') {
              marker = this.timestampToMarker(input);
              instantMs = input;
          }
          else if (input instanceof Date) {
              input = input.valueOf();
              if (!isNaN(input)) {
                  marker = this.timestampToMarker(input);
                  instantMs = input;
              }
          }
          else if (Array.isArray(input)) {
              marker = arrayToUtcDate(input);
          }
          if (marker === null || !isValidDate(marker)) {
              return null;
          }
          return { marker, isTimeUnspecified: false, instantMs };
      }
      parse(s) {
          let parts = parse(s);
          if (parts === null) {
              return null;
          }
          let { marker } = parts;
          let instantMs;
          if (parts.timeZoneOffset !== null) {
              instantMs = marker.valueOf() - parts.timeZoneOffset * 60 * 1000;
              marker = this.timestampToMarker(instantMs);
          }
          return { marker, isTimeUnspecified: parts.isTimeUnspecified, instantMs };
      }
      // Accessors
      getYear(marker) {
          return this.calendarSystem.getMarkerYear(marker);
      }
      getMonth(marker) {
          return this.calendarSystem.getMarkerMonth(marker);
      }
      getDay(marker) {
          return this.calendarSystem.getMarkerDay(marker);
      }
      // Adding / Subtracting
      add(marker, dur) {
          let a = this.calendarSystem.markerToArray(marker);
          a[0] += dur.years;
          a[1] += dur.months;
          a[2] += dur.days;
          a[6] += dur.milliseconds;
          return this.calendarSystem.arrayToMarker(a);
      }
      subtract(marker, dur) {
          let a = this.calendarSystem.markerToArray(marker);
          a[0] -= dur.years;
          a[1] -= dur.months;
          a[2] -= dur.days;
          a[6] -= dur.milliseconds;
          return this.calendarSystem.arrayToMarker(a);
      }
      addYears(marker, n) {
          let a = this.calendarSystem.markerToArray(marker);
          a[0] += n;
          return this.calendarSystem.arrayToMarker(a);
      }
      addMonths(marker, n) {
          let a = this.calendarSystem.markerToArray(marker);
          a[1] += n;
          return this.calendarSystem.arrayToMarker(a);
      }
      // Diffing Whole Units
      diffWholeYears(m0, m1) {
          let { calendarSystem } = this;
          if (timeAsMs(m0) === timeAsMs(m1) &&
              calendarSystem.getMarkerDay(m0) === calendarSystem.getMarkerDay(m1) &&
              calendarSystem.getMarkerMonth(m0) === calendarSystem.getMarkerMonth(m1)) {
              return calendarSystem.getMarkerYear(m1) - calendarSystem.getMarkerYear(m0);
          }
          return null;
      }
      diffWholeMonths(m0, m1) {
          let { calendarSystem } = this;
          if (timeAsMs(m0) === timeAsMs(m1) &&
              calendarSystem.getMarkerDay(m0) === calendarSystem.getMarkerDay(m1)) {
              return (calendarSystem.getMarkerMonth(m1) - calendarSystem.getMarkerMonth(m0)) +
                  (calendarSystem.getMarkerYear(m1) - calendarSystem.getMarkerYear(m0)) * 12;
          }
          return null;
      }
      // Range / Duration
      greatestWholeUnit(m0, m1) {
          let n = this.diffWholeYears(m0, m1);
          if (n !== null) {
              return { unit: 'year', value: n };
          }
          n = this.diffWholeMonths(m0, m1);
          if (n !== null) {
              return { unit: 'month', value: n };
          }
          n = diffWholeWeeks(m0, m1);
          if (n !== null) {
              return { unit: 'week', value: n };
          }
          n = diffWholeDays(m0, m1);
          if (n !== null) {
              return { unit: 'day', value: n };
          }
          n = diffHours(m0, m1);
          if (isInt(n)) {
              return { unit: 'hour', value: n };
          }
          n = diffMinutes(m0, m1);
          if (isInt(n)) {
              return { unit: 'minute', value: n };
          }
          n = diffSeconds(m0, m1);
          if (isInt(n)) {
              return { unit: 'second', value: n };
          }
          return { unit: 'millisecond', value: m1.valueOf() - m0.valueOf() };
      }
      countDurationsBetween(m0, m1, d) {
          // TODO: can use greatestWholeUnit
          let diff;
          if (d.years) {
              diff = this.diffWholeYears(m0, m1);
              if (diff !== null) {
                  return diff / asRoughYears(d);
              }
          }
          if (d.months) {
              diff = this.diffWholeMonths(m0, m1);
              if (diff !== null) {
                  return diff / asRoughMonths(d);
              }
          }
          if (d.days) {
              diff = diffWholeDays(m0, m1);
              if (diff !== null) {
                  return diff / asRoughDays(d);
              }
          }
          return (m1.valueOf() - m0.valueOf()) / asRoughMs(d);
      }
      // Start-Of
      // these DON'T return zoned-dates. only UTC start-of dates
      startOf(m, unit) {
          if (unit === 'year') {
              return this.startOfYear(m);
          }
          if (unit === 'month') {
              return this.startOfMonth(m);
          }
          if (unit === 'week') {
              return this.startOfWeek(m);
          }
          if (unit === 'day') {
              return startOfDay(m);
          }
          if (unit === 'hour') {
              return startOfHour(m);
          }
          if (unit === 'minute') {
              return startOfMinute(m);
          }
          if (unit === 'second') {
              return startOfSecond(m);
          }
          return null;
      }
      startOfYear(m) {
          return this.calendarSystem.arrayToMarker([
              this.calendarSystem.getMarkerYear(m),
          ]);
      }
      startOfMonth(m) {
          return this.calendarSystem.arrayToMarker([
              this.calendarSystem.getMarkerYear(m),
              this.calendarSystem.getMarkerMonth(m),
          ]);
      }
      startOfWeek(m) {
          return this.calendarSystem.arrayToMarker([
              this.calendarSystem.getMarkerYear(m),
              this.calendarSystem.getMarkerMonth(m),
              m.getUTCDate() - ((m.getUTCDay() - this.weekDow + 7) % 7),
          ]);
      }
      // Week Number
      computeWeekNumber(marker) {
          if (this.weekNumberFunc) {
              return this.weekNumberFunc(this.toDate(marker));
          }
          return weekOfYear(marker, this.weekDow, this.weekDoy);
      }
      formatToParts(marker, formatter, dateOptions = {}) {
          return formatter.formatToParts(this.toZonedInstant(marker, dateOptions.instantMs), this);
      }
      formatRangeToParts(start, end, formatter, dateOptions = {}) {
          let { endInstantMs } = dateOptions;
          if (dateOptions.isEndExclusive) {
              end = addMs(end, -1);
              if (endInstantMs != null) {
                  endInstantMs -= 1;
              }
          }
          return formatter.formatRangeToParts(this.toZonedInstant(start, dateOptions.startInstantMs), this.toZonedInstant(end, endInstantMs), this);
      }
      // pairs a wall-clock marker with its real epoch instant (first occurrence when the
      // wall-clock is ambiguous), unless an exact instant is supplied. the marker is
      // re-derived from the instant so the pair always agrees, even when the given marker
      // was nonexistent (DST gap) or expressed in a different offset's reading
      toZonedInstant(marker, instantMs) {
          if (instantMs == null) {
              instantMs = this.toDate(marker).valueOf();
          }
          return { marker: this.timestampToMarker(instantMs), instantMs };
      }
      /*
      DUMB: the omitTime arg is dumb. if we omit the time, we want to omit the timezone offset. and if we do that,
      might as well use buildIsoString or some other util directly
      */
      formatIso(marker, extraOptions = {}) {
          let timeZoneOffset = null;
          if (!extraOptions.omitTimeZoneOffset) {
              timeZoneOffset = this.offsetForMarker(marker);
          }
          return buildIsoString(marker, timeZoneOffset, extraOptions.omitTime);
      }
      // TimeZone
      timestampToMarker(ms) {
          if (this.timeZone === 'local') {
              return arrayToUtcDate(dateToLocalArray(new Date(ms)));
          }
          if (this.timeZone === 'UTC') {
              return new Date(ms);
          }
          const zdt = toZonedDateTimeISO(fromEpochMilliseconds(ms), this.timeZone);
          return new Date(// a "Date Marker", which is like PlainDateTime
          Date.UTC(zdt.year, zdt.month - 1, zdt.day, zdt.hour, zdt.minute, zdt.second, zdt.millisecond));
      }
      offsetForMarker(m) {
          if (this.timeZone === 'local') {
              return -arrayToLocalDate(dateToUtcArray(m)).getTimezoneOffset(); // convert "inverse" offset to "normal" offset
          }
          if (this.timeZone === 'UTC') {
              return 0;
          }
          return offsetNanoseconds(toZonedDateTime(create(m.getUTCFullYear(), m.getUTCMonth() + 1, m.getUTCDate(), m.getUTCHours(), m.getUTCMinutes(), m.getUTCSeconds(), m.getUTCMilliseconds()), this.timeZone)) / (1000000000 * 60);
      }
      // Conversion
      toDate(m) {
          if (this.timeZone === 'local') {
              return arrayToLocalDate(dateToUtcArray(m));
          }
          if (this.timeZone === 'UTC') {
              return new Date(m.valueOf()); // make sure it's a copy
          }
          return new Date(toZonedDateTime(create(m.getUTCFullYear(), m.getUTCMonth() + 1, m.getUTCDate(), m.getUTCHours(), m.getUTCMinutes(), m.getUTCSeconds(), m.getUTCMilliseconds()), this.timeZone).epochMilliseconds);
      }
  }

  const EXTENDED_SETTINGS = new Set([
      'week',
      'meridiem',
      'omitZeroMinute',
      'omitCommas',
      'forceCommas',
      'omitTrailing',
      'weekdayJustify',
  ]);
  const MERIDIEM_RE = /([ap])\.?m\.?/i;
  const COMMA_RE = /,/g;
  const LTR_RE = /\u200e/g; // control character
  const TRAILING_RE = /[\s.,]+$/;
  const WHITESPACE_ONLY_RE = /^\s+$/;
  class NativeDateFormatter {
      constructor(options) {
          const standardOptions = {};
          const extendedOptions = {};
          for (const name in options) {
              if (EXTENDED_SETTINGS.has(name)) {
                  extendedOptions[name] = options[name];
              }
              else {
                  standardOptions[name] = options[name];
              }
          }
          // all zone-name requests render as offsets ("GMT-4") for now, matching the historical
          // synthesized style. flipping to real zone names ("EDT") is a deliberate future change
          if (standardOptions.timeZoneName) {
              standardOptions.timeZoneName = 'shortOffset';
          }
          this.timeZoneOnly = Object.keys(standardOptions).length === 1 &&
              Boolean(standardOptions.timeZoneName);
          this.weekOnly = Boolean(!Object.keys(standardOptions).length && extendedOptions.week);
          if (!this.timeZoneOnly) {
              if (standardOptions.timeZoneName) {
                  if (!standardOptions.hour) {
                      standardOptions.hour = '2-digit';
                  }
                  if (!standardOptions.minute) {
                      standardOptions.minute = '2-digit';
                  }
              }
              if (extendedOptions.omitZeroMinute &&
                  (standardOptions.second || standardOptions.fractionalSecondDigits)) {
                  delete extendedOptions.omitZeroMinute;
              }
          }
          this.standardOptions = standardOptions;
          this.extendedOptions = extendedOptions;
      }
      formatToParts(date, context) {
          const { extendedOptions } = this;
          if (this.timeZoneOnly) {
              return this.getFormats(context).normalFormat
                  .formatToParts(date.instantMs)
                  .filter((part) => part.type === 'timeZoneName');
          }
          if (this.weekOnly) {
              return formatWeekNumberParts(context.computeWeekNumber(date.marker), context.weekTextLong, context.weekTextShort, context.locale, extendedOptions.week);
          }
          const { normalFormat, zeroFormat } = this.getFormats(context);
          const format = (zeroFormat && !date.marker.getUTCMinutes())
              ? zeroFormat
              : normalFormat;
          const parts = format.formatToParts(date.instantMs);
          return postProcessParts(parts, extendedOptions);
      }
      formatRangeToParts(start, end, context) {
          const { extendedOptions } = this;
          if (this.timeZoneOnly || this.weekOnly) {
              return this.formatToParts(start, context).map((part) => {
                  return {
                      source: part.type === 'literal' ? 'shared' : 'startRange',
                      ...part,
                  };
              });
          }
          const { normalFormat, zeroFormat } = this.getFormats(context);
          const format = (zeroFormat && !start.marker.getUTCMinutes() && !end.marker.getUTCMinutes())
              ? zeroFormat
              : normalFormat;
          // the instants are real and ordered, so Intl's rendering is authoritative. ICU's
          // interval output currently omits zone names and collapses equal-wall-clock
          // endpoints — upstream limitations we deliberately do not paper over
          const parts = format.formatRangeToParts(start.instantMs, end.instantMs);
          return postProcessRangeParts(parts, extendedOptions);
      }
      getFormats(context) {
          if (this.cachedContext !== context) {
              const { extendedOptions } = this;
              const { codes } = context.locale;
              const standardOptions = {
                  ...this.standardOptions,
                  // 'local' means the system zone, which is Intl's default
                  timeZone: context.timeZone === 'local' ? undefined : context.timeZone,
              };
              const normalFormat = new Intl.DateTimeFormat(codes, standardOptions);
              let zeroFormat;
              if (extendedOptions.omitZeroMinute) {
                  const zeroProps = { ...standardOptions };
                  delete zeroProps.minute;
                  zeroFormat = new Intl.DateTimeFormat(codes, zeroProps);
              }
              this.cachedContext = context;
              this.cachedFormats = { normalFormat, zeroFormat };
          }
          return this.cachedFormats;
      }
  }
  function processPartsLoop(parts, extendedOptions) {
      let priorLiteral;
      for (const part of parts) {
          const isLiteral = part.type === 'literal';
          if (isLiteral || part.type === 'dayPeriod') {
              let s = part.value;
              s = s.replace(LTR_RE, '');
              if (extendedOptions.omitCommas) {
                  s = s.replace(COMMA_RE, '');
              }
              if (!isLiteral) {
                  const { meridiem } = extendedOptions;
                  if (meridiem === false) {
                      s = s.replace(MERIDIEM_RE, '');
                  }
                  else if (meridiem === 'narrow') {
                      s = s.replace(MERIDIEM_RE, (_m0, m1) => m1.toLocaleLowerCase());
                  }
                  else if (meridiem === 'short') {
                      s = s.replace(MERIDIEM_RE, (_m0, m1) => `${m1.toLocaleLowerCase()}m`);
                  }
                  else if (meridiem === 'lowercase') {
                      s = s.replace(MERIDIEM_RE, (m0) => m0.toLocaleLowerCase());
                  }
                  if (priorLiteral) {
                      priorLiteral.value = priorLiteral.value.trimEnd();
                  }
              }
              part.value = s;
          }
          priorLiteral = isLiteral ? part : undefined;
      }
  }
  function postProcessParts(parts, extendedOptions) {
      processPartsLoop(parts, extendedOptions);
      if (extendedOptions.weekdayJustify &&
          parts.length === 3 &&
          WHITESPACE_ONLY_RE.test(parts[1].value)) {
          if (parts[extendedOptions.weekdayJustify === 'start' ? 2 : 0].type === 'weekday') {
              parts.reverse();
          }
      }
      if (extendedOptions.forceCommas) {
          for (const part of parts) {
              if (part.type === 'literal' && WHITESPACE_ONLY_RE.test(part.value)) {
                  part.value = `,${part.value}`;
              }
          }
      }
      if (extendedOptions.omitTrailing) {
          stripTrailingLiteral(parts);
      }
      return parts.filter((part) => part.value);
  }
  function postProcessRangeParts(parts, extendedOptions) {
      processPartsLoop(parts, extendedOptions);
      if (extendedOptions.forceCommas) {
          for (const part of parts) {
              if (part.type === 'literal' && WHITESPACE_ONLY_RE.test(part.value)) {
                  part.value = `,${part.value}`;
              }
          }
      }
      if (extendedOptions.omitTrailing) {
          stripTrailingLiteral(parts);
      }
      return parts.filter((part) => part.value);
  }
  function stripTrailingLiteral(parts) {
      const lastPart = parts[parts.length - 1];
      if (lastPart?.type === 'literal') {
          lastPart.value = lastPart.value.replace(TRAILING_RE, '');
          if (!lastPart.value) {
              parts.pop();
          }
      }
  }
  function formatWeekNumberParts(num, weekTextLong, weekTextShort, locale, display) {
      const parts = [];
      if (display === 'long') {
          parts.push({ type: 'literal', value: weekTextLong });
      }
      else if (display === 'short' || display === 'narrow') {
          parts.push({ type: 'literal', value: weekTextShort });
      }
      if (display === 'long' || display === 'short') {
          parts.push({ type: 'literal', value: ' ' });
      }
      parts.push({
          type: 'week',
          value: locale.simpleNumberFormat.format(num),
      });
      if (locale.options.direction === 'rtl') {
          parts.reverse();
      }
      return parts;
  }

  class CmdDateFormatter {
      constructor(cmdStr) {
          this.cmdStr = cmdStr;
      }
      formatToParts(date, context) {
          const res = context.cmdFormatter(this.cmdStr, createVerboseFormattingArg(date, null, context));
          if (Array.isArray(res)) {
              return res;
          }
          return [{ type: 'literal', value: res }];
      }
      formatRangeToParts(start, end, context) {
          const res = context.cmdFormatter(this.cmdStr, createVerboseFormattingArg(start, end, context));
          if (Array.isArray(res)) {
              return res.map((part) => ({
                  source: 'shared',
                  ...part,
              }));
          }
          return [{ source: 'shared', type: 'literal', value: res }];
      }
  }

  class FuncDateFormatter {
      constructor(func) {
          this.func = func;
      }
      formatToParts(date, context) {
          const str = this.func(createVerboseFormattingArg(date, null, context));
          return [{ type: 'literal', value: str }];
      }
      formatRangeToParts(start, end, context) {
          const str = this.func(createVerboseFormattingArg(start, end, context));
          return [{ source: 'shared', type: 'literal', value: str }];
      }
  }

  var classNames = {"popoverZ":"fc-1U","isolate":"fc-1q","borderBoxRoot":"fc-pp","notAllowed":"fc-gm","noScrollbars":"fc-xp","noShrink":"fc-J9","calendarScreenRoot":"fc-oi","safeTiles":"fc-TV","calendarPrintRoot":"fc-OY","cursorPointer":"fc-ky","cursorResizeT":"fc-Wq","cursorResizeB":"fc-2H","cursorResizeS":"fc-lP","cursorResizeE":"fc-pu","cursorColResizer":"fc-Mo","hit":"fc-Bx","hitX":"fc-rT","hitY":"fc-1e","hitXSkinny":"fc-7U","selectNone":"fc-N6","invisible":"fc-BW","borderless":"fc-rf","borderlessX":"fc-Nq","borderlessY":"fc-zp","borderlessTop":"fc-1h","borderlessBottom":"fc-cZ","borderlessStart":"fc-G8","borderlessEnd":"fc-MA","flexRow":"fc-Dh","flexCol":"fc-vg","grow":"fc-85","liquid":"fc-91","minHeight0":"fc-Da","liquidX":"fc-1v","printTable":"fc-uR","noPadding":"fc-hF","noPaddingY":"fc-Ds","noMargin":"fc-TA","noMarginY":"fc-rt","noMarginX":"fc-wS","whiteSpaceNoWrap":"fc-mV","whiteSpacePre":"fc-zJ","overflowAnchorNone":"fc-Fk","pointerEventsNone":"fc-Ss","crop":"fc-D6","cropNowrap":"fc-5x","rel":"fc-DP","abs":"fc-P2","start0":"fc-5a","end0":"fc-lb","fill":"fc-0X","fillTop":"fc-9s","fillX":"fc-Gk","fillY":"fc-xh","fillStart":"fc-XV","sticky":"fc-XI","stickyT":"fc-7G","stickyS":"fc-Rw","tableHeaderSticky":"fc-yg","contentBox":"fc-2i","offscreen":"fc-o2","alignCenter":"fc-ih","alignStart":"fc-HJ","alignEnd":"fc-El","footerScrollbarSticky":"fc-nF","footerScrollbar":"fc-Or","breakInsideAvoid":"fc-6w","printCellContentMinHeight":"fc-9C","flowRoot":"fc-GJ","z0":"fc-d0","z1":"fc-Og","z2":"fc-BT","z3":"fc-XO","z4":"fc-e8","z5":"fc-sR","z1000":"fc-W4","z9999":"fc-eV","focusZ2":"fc-4U","internalTimelineSlot":"fc-YC","internalEvent":"fc-M0","internalEventMirror":"fc-N9","internalEventDraggable":"fc-41","internalEventSelected":"fc-vO","internalEventResizable":"fc-i0","internalEventResizer":"fc-Nc","internalEventResizerStart":"fc-hg","internalEventResizerEnd":"fc-dk","internalBgEvent":"fc-aw","internalMoreLink":"fc-kw","internalNavLink":"fc-Zy","internalPopover":"fc-ox","internalView":"fc-Q3","internalScroller":"fc-P4"};

  function joinClassNames(...args) {
      return args.filter(Boolean).join(' ');
  }
  /*
  TODO: dedup with @full-ui/headless-grid somehow
  */
  function fracToCssDim(frac) {
      return frac * 100 + '%';
  }

  function createFormatter(input) {
      if (typeof input === 'object' && input) { // non-null object
          return new NativeDateFormatter(input);
      }
      if (typeof input === 'string') {
          return new CmdDateFormatter(input);
      }
      if (typeof input === 'function') {
          return new FuncDateFormatter(input);
      }
      return null;
  }

  function warn(...args) {
      console.warn('FullCalendar:', ...args);
  }

  /* eslint max-classes-per-file: off */
  const warnedClassNameOptions = {};
  function refineClassName(input, optionName) {
      if (!input || typeof input === 'string') {
          return input;
      }
      warnInvalidClassName(optionName);
      return '';
  }
  function refineClassNameGenerator(input, optionName) {
      if (typeof input === 'function') {
          return (renderProps) => refineClassName(input(renderProps), optionName);
      }
      return refineClassName(input, optionName);
  }
  function warnInvalidClassName(optionName) {
      if (!warnedClassNameOptions[optionName]) {
          warn(`Invalid option \`${optionName}\`: expected a className string or a falsy value.`);
          warnedClassNameOptions[optionName] = true;
      }
  }

  // Stops a mouse/touch event from doing it's native browser action
  function preventDefault(ev) {
      ev.preventDefault();
  }
  // Event Delegation
  // ----------------------------------------------------------------------------------------------------------------
  function buildDelegationHandler(selector, handler) {
      return (ev) => {
          let matchedChild = ev.target.closest(selector);
          if (matchedChild) {
              handler.call(matchedChild, ev, matchedChild);
          }
      };
  }
  function listenBySelector(container, eventType, selector, handler) {
      let attachedHandler = buildDelegationHandler(selector, handler);
      container.addEventListener(eventType, attachedHandler);
      return () => {
          container.removeEventListener(eventType, attachedHandler);
      };
  }
  function listenToHoverBySelector(container, selector, onMouseEnter, onMouseLeave) {
      let currentMatchedChild;
      return listenBySelector(container, 'mouseover', selector, (mouseOverEv, matchedChild) => {
          if (matchedChild !== currentMatchedChild) {
              currentMatchedChild = matchedChild;
              onMouseEnter(mouseOverEv, matchedChild);
              let realOnMouseLeave = (mouseLeaveEv) => {
                  currentMatchedChild = null;
                  onMouseLeave(mouseLeaveEv, matchedChild);
                  matchedChild.removeEventListener('mouseleave', realOnMouseLeave);
              };
              // listen to the next mouseleave, and then unattach
              matchedChild.addEventListener('mouseleave', realOnMouseLeave);
          }
      });
  }
  // Animation
  // ----------------------------------------------------------------------------------------------------------------
  const transitionEventNames = [
      'webkitTransitionEnd',
      'otransitionend',
      'oTransitionEnd',
      'msTransitionEnd',
      'transitionend',
  ];
  // triggered only when the next single subsequent transition finishes
  function whenTransitionDone(el, callback) {
      let realCallback = (ev) => {
          callback(ev);
          transitionEventNames.forEach((eventName) => {
              el.removeEventListener(eventName, realCallback);
          });
      };
      transitionEventNames.forEach((eventName) => {
          el.addEventListener(eventName, realCallback); // cross-browser way to determine when the transition finishes
      });
  }
  // ARIA workarounds
  // ----------------------------------------------------------------------------------------------------------------
  function createAriaClickAttrs(handler) {
      return {
          onClick: handler,
          ...createAriaKeyboardAttrs(handler),
      };
  }
  function createAriaKeyboardAttrs(handler) {
      return {
          tabIndex: 0,
          onKeyDown(ev) {
              if (ev.key === 'Enter' || ev.key === ' ') {
                  handler(ev);
                  ev.preventDefault(); // if space, don't scroll down page
              }
          },
      };
  }

  let guidNumber = 0;
  function guid() {
      guidNumber += 1;
      return String(guidNumber);
  }
  /* FullCalendar-specific DOM Utilities
  ----------------------------------------------------------------------------------------------------------------------*/
  // Make the mouse cursor express that an event is not allowed in the current area
  function disableCursor() {
      document.body.classList.add(classNames.notAllowed);
  }
  // Returns the mouse cursor to its original look
  function enableCursor() {
      document.body.classList.remove(classNames.notAllowed);
  }
  /* Selection
  ----------------------------------------------------------------------------------------------------------------------*/
  function preventSelection(el) {
      el.style.userSelect = 'none';
      el.style.webkitUserSelect = 'none';
      el.addEventListener('selectstart', preventDefault);
  }
  function allowSelection(el) {
      el.style.userSelect = '';
      el.style.webkitUserSelect = '';
      el.removeEventListener('selectstart', preventDefault);
  }
  /* Context Menu
  ----------------------------------------------------------------------------------------------------------------------*/
  function preventContextMenu(el) {
      el.addEventListener('contextmenu', preventDefault);
  }
  function allowContextMenu(el) {
      el.removeEventListener('contextmenu', preventDefault);
  }
  function parseFieldSpecs(input) {
      let specs = [];
      let tokens = [];
      let i;
      let token;
      if (typeof input === 'string') {
          tokens = input.split(/\s*,\s*/);
      }
      else if (typeof input === 'function') {
          tokens = [input];
      }
      else if (Array.isArray(input)) {
          tokens = input;
      }
      for (i = 0; i < tokens.length; i += 1) {
          token = tokens[i];
          if (typeof token === 'string') {
              specs.push(token.charAt(0) === '-' ?
                  { field: token.substring(1), order: -1 } :
                  { field: token, order: 1 });
          }
          else if (typeof token === 'function') {
              specs.push({ func: token });
          }
      }
      return specs;
  }
  function compareByFieldSpecs(obj0, obj1, fieldSpecs) {
      let i;
      let cmp;
      for (i = 0; i < fieldSpecs.length; i += 1) {
          cmp = compareByFieldSpec(obj0, obj1, fieldSpecs[i]);
          if (cmp) {
              return cmp;
          }
      }
      return 0;
  }
  function compareByFieldSpec(obj0, obj1, fieldSpec) {
      if (fieldSpec.func) {
          return fieldSpec.func(obj0, obj1);
      }
      return flexibleCompare(obj0[fieldSpec.field], obj1[fieldSpec.field])
          * (fieldSpec.order || 1);
  }
  function flexibleCompare(a, b) {
      if (!a && !b) {
          return 0;
      }
      if (b == null) {
          return -1;
      }
      if (a == null) {
          return 1;
      }
      if (typeof a === 'string' || typeof b === 'string') {
          return String(a).localeCompare(String(b));
      }
      return a - b;
  }
  /* String Utilities
  ----------------------------------------------------------------------------------------------------------------------*/
  function formatWithOrdinals(formatter, args, fallbackText) {
      if (typeof formatter === 'function') {
          return formatter(...args);
      }
      if (typeof formatter === 'string') { // non-blank string
          return args.reduce((str, arg, index) => (str.replace('$' + index, arg || '')), formatter);
      }
      return fallbackText;
  }
  /* Number Utilities
  ----------------------------------------------------------------------------------------------------------------------*/
  function compareNumbers(a, b) {
      return a - b;
  }
  function valuesIdentical(a, b) {
      return a === b;
  }
  function computeViewBorderless(options) {
      const borderless = options.borderless;
      return {
          borderlessX: Boolean(options.borderlessX ?? borderless),
          borderlessTop: Boolean(options.borderlessTop ?? borderless),
          borderlessBottom: Boolean(options.borderlessBottom ?? borderless),
      };
  }

  const { hasOwnProperty } = Object.prototype;
  // Filter / Map
  // -------------------------------------------------------------------------------------------------
  function filterHash(hash, func) {
      let filtered = {};
      for (let key in hash) {
          if (func(hash[key], key)) {
              filtered[key] = hash[key];
          }
      }
      return filtered;
  }
  function mapHash(hash, func) {
      let newHash = {};
      for (let key in hash) {
          newHash[key] = func(hash[key], key);
      }
      return newHash;
  }
  // Conversion
  // -------------------------------------------------------------------------------------------------
  // Can't use Object.values yet because no es2015 support
  // TODO: reassess browser support
  // https://caniuse.com/?search=object.values
  function hashValuesToArray(obj) {
      let a = [];
      for (let key in obj) {
          a.push(obj[key]);
      }
      return a;
  }
  // TODO: rename to stringArrayToHash or something
  function arrayToHash(a) {
      let hash = {};
      for (let item of a) {
          hash[item] = true;
      }
      return hash;
  }
  // Equality
  // -------------------------------------------------------------------------------------------------
  function isMaybePropsEqualDepth1(props0, props1) {
      if (typeof props0 === 'object' && props0 && // non-null object
          typeof props1 === 'object' && props1 // non-null object
      ) {
          return isPropsEqualWithFunc(props0, props1, isPropsEqualShallow);
      }
      return props0 === props1;
  }
  function isPropsEqualWithFunc(props0, props1, valuesEqual) {
      if (props0 === props1) {
          return true;
      }
      for (let key in props0) {
          if (hasOwnProperty.call(props0, key)) {
              if (!(key in props1)) {
                  return false;
              }
          }
      }
      for (let key in props1) {
          if (hasOwnProperty.call(props1, key)) {
              if (!(key in props0) || !valuesEqual(props0[key], props1[key], key)) {
                  return false;
              }
          }
      }
      return true;
  }
  function isMaybePropsEqualShallow(props0, props1) {
      if (typeof props0 === 'object' &&
          typeof props1 === 'object' &&
          props0 && props1 // both non-null objects
      ) {
          return isPropsEqualShallow(props0, props1);
      }
      return props0 === props1;
  }
  function isPropsEqualShallow(props0, props1) {
      return isPropsEqualWithFunc(props0, props1, valuesIdentical);
  }
  function isPropsEqualWithMap(props0, props1, equalityFuncMap) {
      return isPropsEqualWithFunc(props0, props1, (val0, val1, key) => {
          const equalityFunc = equalityFuncMap[key];
          const isEqual = equalityFunc
              ? equalityFunc(val0, val1)
              : val0 === val1;
          // if (debugMessage && !isEqual) {
          //   console.log(
          //     debugMessage, key, 'NOT EQUAL', 'rerunning...',
          //     equalityFunc
          //       ? equalityFunc(val0, val1)
          //       : val0 === val1
          //   )
          // }
          return isEqual;
      });
  }
  /*
  Returns array of keys
  */
  function getUnequalProps(props0, props1) {
      let keys = [];
      for (let key in props0) {
          if (hasOwnProperty.call(props0, key)) {
              if (!(key in props1)) {
                  keys.push(key);
              }
          }
      }
      for (let key in props1) {
          if (hasOwnProperty.call(props1, key)) {
              if (props0[key] !== props1[key]) {
                  keys.push(key);
              }
          }
      }
      return keys;
  }
  // Merge
  // -------------------------------------------------------------------------------------------------
  function mergeMaybePropsDepth1(props0, props1) {
      if (!props0) {
          return props1;
      }
      return mergePropsWithFunc(props0, props1, mergePropsShallow);
  }
  function mergePropsWithFunc(props0, props1, mergeValues) {
      const dest = {};
      for (let key in props0) {
          if (hasOwnProperty.call(props0, key)) {
              if (!(key in props1)) {
                  dest[key] = props0[key];
              }
          }
      }
      for (let key in props1) {
          if (hasOwnProperty.call(props1, key)) {
              if (!(key in props0)) {
                  dest[key] = props1[key];
              }
              else {
                  dest[key] = mergeValues(props0[key], props1[key]);
              }
          }
      }
      return dest;
  }
  function mergePropsShallow(props0, props1) {
      return Object.assign({}, props0, props1);
  }

  // TODO: new util arrayify?
  // Array.prototype.slice.call(
  function flatArray(items) {
      const res = [];
      for (const item of items) {
          if (Array.isArray(item)) {
              for (const subItem of item) {
                  res.push(subItem);
              }
          }
          else {
              res.push(item);
          }
      }
      return res;
  }
  function flatMapArray(inputs, mapFunc) {
      const res = [];
      for (let i = 0; i < inputs.length; i += 1) {
          const output = mapFunc(inputs[i], i);
          if (Array.isArray(output)) {
              for (const subOutput of output) {
                  res.push(subOutput);
              }
          }
          else {
              res.push(output);
          }
      }
      return res;
  }
  function removeExact(array, exactItem) {
      let removeCnt = 0;
      let i = 0;
      while (i < array.length) {
          if (array[i] === exactItem) {
              array.splice(i, 1);
              removeCnt += 1;
          }
          else {
              i += 1;
          }
      }
      return removeCnt;
  }
  function isMaybeArraysEqual(array0, array1) {
      if (Array.isArray(array0) && Array.isArray(array1)) {
          return isArraysEqual(array0, array1);
      }
      return array0 === array1;
  }
  function isArraysEqual(array0, array1, itemsEqual = valuesIdentical) {
      if (array0 === array1) {
          return true;
      }
      let len = array0.length;
      let i;
      if (len !== array1.length) { // not array? or not same length?
          return false;
      }
      for (i = 0; i < len; i += 1) {
          if (!itemsEqual(array0[i], array1[i])) {
              return false;
          }
      }
      return true;
  }

  // base options
  // ------------
  const BASE_OPTION_REFINERS = {
      navLinkDayClick: identity,
      navLinkWeekClick: identity,
      duration: createDuration,
      buttons: identity,
      toolbarElements: identity,
      prevText: String,
      nextText: String,
      prevYearText: String,
      nextYearText: String,
      todayText: String,
      yearText: String,
      monthText: String,
      weekTextLong: String,
      weekTextShort: String,
      dayText: String,
      listText: identity,
      todayHint: identity,
      prevHint: identity,
      nextHint: identity,
      // TODO: make type for hint input
      buttonDisplay: identity,
      buttonGroupClass: refineClassNameGenerator,
      buttonClass: refineClassNameGenerator,
      defaultAllDayEventDuration: createDuration,
      defaultTimedEventDuration: createDuration,
      nextDayThreshold: createDuration,
      scrollTime: createDuration,
      scrollTimeReset: Boolean,
      slotMinTime: createDuration,
      slotMaxTime: createDuration,
      popoverFormat: createFormatter,
      slotDuration: createDuration,
      snapDuration: createDuration,
      headerToolbar: identity,
      footerToolbar: identity,
      forceEventDuration: Boolean,
      // TODO: move to timegrid
      dayLaneClass: refineClassNameGenerator,
      dayLaneInnerClass: refineClassNameGenerator,
      dayLaneDidMount: identity,
      dayLaneWillUnmount: identity,
      initialView: String,
      aspectRatio: Number,
      weekends: Boolean,
      weekNumberCalculation: identity,
      weekNumbers: Boolean,
      weekNumberHeaderClass: refineClassNameGenerator,
      weekNumberHeaderInnerClass: refineClassNameGenerator,
      weekNumberHeaderContent: identity,
      weekNumberHeaderDidMount: identity,
      weekNumberHeaderWillUnmount: identity,
      inlineWeekNumberClass: refineClassNameGenerator,
      inlineWeekNumberContent: identity,
      inlineWeekNumberDidMount: identity,
      inlineWeekNumberWillUnmount: identity,
      editable: Boolean,
      controller: identity,
      nowIndicator: Boolean,
      nowIndicatorSnap: identity,
      nowIndicatorHeaderClass: refineClassNameGenerator,
      nowIndicatorHeaderContent: identity,
      nowIndicatorHeaderDidMount: identity,
      nowIndicatorHeaderWillUnmount: identity,
      nowIndicatorDotClass: refineClassName,
      nowIndicatorLineClass: refineClassNameGenerator,
      nowIndicatorLineContent: identity,
      nowIndicatorLineDidMount: identity,
      nowIndicatorLineWillUnmount: identity,
      showNonCurrentDates: Boolean,
      lazyFetching: Boolean,
      startParam: String,
      endParam: String,
      timeZoneParam: String,
      timeZone: String,
      locales: identity,
      locale: identity,
      dragRevertDuration: Number,
      dragScroll: Boolean,
      allDayMaintainDuration: Boolean,
      unselectAuto: Boolean,
      dropAccept: identity, // TODO: type draggable
      eventOrder: parseFieldSpecs,
      eventOrderStrict: Boolean,
      eventSlicing: Boolean, // default: true
      eventPrintLayout: String,
      longPressDelay: Number,
      eventDragMinDistance: Number,
      expandRows: Boolean,
      height: identity,
      contentHeight: identity,
      direction: String,
      colorScheme: String,
      weekNumberFormat: createFormatter,
      eventResizableFromStart: Boolean,
      displayEventTime: Boolean,
      displayEventEnd: Boolean,
      progressiveEventRendering: Boolean,
      businessHours: identity,
      initialDate: identity,
      now: identity,
      eventDataTransform: identity,
      tableHeaderSticky: identity,
      footerScrollbarSticky: identity,
      defaultAllDay: Boolean,
      eventSourceFailure: identity,
      eventSourceSuccess: identity,
      eventDisplay: String, // TODO: give more specific
      eventStartEditable: Boolean,
      eventDurationEditable: Boolean,
      eventOverlap: identity,
      eventConstraint: identity,
      eventAllow: identity,
      eventColor: String,
      eventContrastColor: String,
      eventDidMount: identity,
      eventWillUnmount: identity,
      eventContent: identity,
      eventClass: refineClassNameGenerator,
      eventInnerClass: refineClassNameGenerator,
      eventTimeClass: refineClassNameGenerator,
      eventTitleClass: refineClassNameGenerator,
      eventBeforeClass: refineClassNameGenerator,
      eventAfterClass: refineClassNameGenerator,
      //
      listItemEventClass: refineClassNameGenerator,
      listItemEventInnerClass: refineClassNameGenerator,
      listItemEventTimeClass: refineClassNameGenerator,
      listItemEventTitleClass: refineClassNameGenerator,
      listItemEventBeforeClass: refineClassNameGenerator,
      listItemEventAfterClass: refineClassNameGenerator,
      //
      blockEventClass: refineClassNameGenerator,
      blockEventInnerClass: refineClassNameGenerator,
      blockEventTimeClass: refineClassNameGenerator,
      blockEventTitleClass: refineClassNameGenerator,
      blockEventBeforeClass: refineClassNameGenerator,
      blockEventAfterClass: refineClassNameGenerator,
      //
      rowEventClass: refineClassNameGenerator,
      rowEventInnerClass: refineClassNameGenerator,
      rowEventTimeClass: refineClassNameGenerator,
      rowEventTitleClass: refineClassNameGenerator,
      rowEventTitleSticky: Boolean,
      rowEventBeforeClass: refineClassNameGenerator,
      rowEventBeforeContent: identity,
      rowEventAfterClass: refineClassNameGenerator,
      rowEventAfterContent: identity,
      //
      columnEventClass: refineClassNameGenerator,
      columnEventInnerClass: refineClassNameGenerator,
      columnEventTimeClass: refineClassNameGenerator,
      columnEventTitleClass: refineClassNameGenerator,
      columnEventTitleSticky: Boolean,
      columnEventBeforeClass: refineClassNameGenerator,
      columnEventAfterClass: refineClassNameGenerator,
      //
      backgroundEventClass: refineClassNameGenerator,
      backgroundEventDidMount: identity,
      backgroundEventWillUnmount: identity,
      backgroundEventContent: identity,
      backgroundEventInnerClass: refineClassNameGenerator,
      backgroundEventTitleClass: refineClassNameGenerator,
      backgroundEventColor: String,
      selectConstraint: identity,
      selectOverlap: identity,
      selectAllow: identity,
      droppable: Boolean,
      unselectCancel: String,
      slotHeaderFormat: identity,
      slotLaneClass: refineClassNameGenerator,
      slotLaneDidMount: identity,
      slotLaneWillUnmount: identity,
      slotHeaderClass: refineClassNameGenerator,
      slotHeaderInnerClass: refineClassNameGenerator,
      slotHeaderContent: identity,
      slotHeaderDidMount: identity,
      slotHeaderWillUnmount: identity,
      slotHeaderAlign: identity,
      slotHeaderSticky: identity,
      slotHeaderRowClass: refineClassName,
      slotHeaderDividerClass: refineClassNameGenerator,
      dayMaxEvents: identity,
      dayMaxEventRows: identity,
      dayMinWidth: Number,
      slotHeaderInterval: createDuration,
      // in core because more-popover needs it
      dayHeaderClass: refineClassNameGenerator,
      dayHeaderInnerClass: refineClassNameGenerator,
      dayHeaderContent: identity,
      dayHeaderDidMount: identity,
      dayHeaderWillUnmount: identity,
      dayHeaderAlign: identity,
      // stickiness for cell-inner-contents laterally. experimental settings
      _dayHeaderSticky: identity,
      dayHeaderRowClass: refineClassName,
      dayHeaderDividerClass: refineClassNameGenerator,
      dayRowClass: refineClassName,
      dayCellDidMount: identity,
      dayCellWillUnmount: identity,
      dayCellClass: refineClassNameGenerator,
      dayCellInnerClass: refineClassNameGenerator,
      dayCellTopContent: identity,
      dayCellTopClass: refineClassNameGenerator,
      dayCellTopInnerClass: refineClassNameGenerator,
      dayCellBottomClass: refineClassNameGenerator,
      allDaySlot: Boolean,
      allDayText: String,
      allDayHeaderClass: refineClassNameGenerator,
      allDayHeaderInnerClass: refineClassNameGenerator,
      allDayHeaderContent: identity,
      allDayHeaderDidMount: identity,
      allDayHeaderWillUnmount: identity,
      timedText: String,
      slotMinWidth: Number,
      slotMinHeight: Number,
      navLinks: Boolean,
      eventTimeFormat: createFormatter,
      rerenderDelay: Number, // TODO: move to vanilla right? nah keep here
      moreLinkText: identity, // this not enforced :( check others too
      moreLinkHint: identity,
      selectMinDistance: Number,
      selectable: Boolean,
      selectLongPressDelay: Number,
      eventLongPressDelay: Number,
      selectMirror: Boolean,
      eventMaxStack: Number,
      eventMinHeight: Number,
      eventMinWidth: Number,
      eventShortHeight: Number,
      slotEventOverlap: Boolean,
      firstDay: Number,
      dayCount: Number,
      dateAlignment: String,
      dateIncrement: createDuration,
      hiddenDays: identity,
      fixedWeekCount: Boolean,
      validRange: identity, // `this` works?
      visibleRange: identity, // `this` works?
      titleFormat: identity,
      eventInteractive: Boolean,
      // only used by list-view, but languages define the value, so we need it in base options
      noEventsText: String,
      viewHint: identity,
      viewChangeHint: String, // for the tab container
      navLinkHint: identity,
      closeHint: String,
      eventsHint: String,
      headingLevel: Number,
      moreLinkClick: identity,
      moreLinkContent: identity,
      moreLinkDidMount: identity,
      moreLinkWillUnmount: identity,
      moreLinkClass: refineClassNameGenerator,
      moreLinkInnerClass: refineClassNameGenerator,
      //
      rowMoreLinkClass: refineClassNameGenerator,
      rowMoreLinkInnerClass: refineClassNameGenerator,
      //
      columnMoreLinkClass: refineClassNameGenerator,
      columnMoreLinkInnerClass: refineClassNameGenerator,
      navLinkClass: refineClassName,
      monthStartFormat: createFormatter,
      dayCellFormat: createFormatter,
      // for connectors
      // (can't be part of plugin system b/c must be provided at runtime)
      handleCustomRendering: identity,
      customRenderingMetaMap: identity,
      popoverClass: refineClassName,
      popoverCloseClass: refineClassName,
      popoverCloseContent: identity,
      dayNarrowWidth: Number,
      borderless: Boolean,
      borderlessX: Boolean,
      borderlessTop: Boolean,
      borderlessBottom: Boolean,
      fillerClass: refineClassNameGenerator,
      headerToolbarClass: refineClassNameGenerator,
      footerToolbarClass: refineClassNameGenerator,
      toolbarClass: refineClassNameGenerator,
      toolbarSectionClass: refineClassNameGenerator,
      toolbarTitleClass: refineClassName,
      tableClass: refineClassNameGenerator,
      tableHeaderClass: refineClassNameGenerator,
      tableBodyClass: refineClassNameGenerator,
      nonBusinessHoursClass: refineClassName,
      highlightClass: refineClassName,
      // daygrid-only
      dayHeaders: Boolean,
      dayHeaderFormat: createFormatter,
      // timegrid-only
      allDayDividerClass: refineClassName,
      // list-only
      listDaysClass: refineClassName, // rename this?
      listDayClass: refineClassNameGenerator,
      //
      listDayFormat: createFalsableFormatter, // defaults specified in list plugins
      listDayAltFormat: createFalsableFormatter, // "
      //
      listDayHeaderDidMount: identity,
      listDayHeaderWillUnmount: identity,
      listDayHeaderClass: refineClassNameGenerator,
      listDayHeaderInnerClass: refineClassNameGenerator,
      listDayHeaderContent: identity,
      //
      listDayBodyClass: refineClassNameGenerator,
      //
      noEventsClass: refineClassNameGenerator,
      noEventsInnerClass: refineClassNameGenerator,
      noEventsContent: identity,
      noEventsDidMount: identity,
      noEventsWillUnmount: identity,
      // noEventsText is defined in base options
      // multimonth-only
      multiMonthMaxColumns: Number,
      //
      singleMonthMinWidth: Number,
      singleMonthTitleFormat: createFormatter,
      singleMonthDidMount: identity,
      singleMonthWillUnmount: identity,
      singleMonthClass: refineClassNameGenerator,
      singleMonthHeaderClass: refineClassNameGenerator,
      singleMonthHeaderInnerClass: refineClassNameGenerator,
  };
  // do NOT give a type here. need `typeof BASE_OPTION_DEFAULTS` to give real results.
  // raw values.
  const BASE_OPTION_DEFAULTS = {
      buttonDisplay: 'auto',
      eventDisplay: 'auto',
      defaultTimedEventDuration: '01:00:00',
      defaultAllDayEventDuration: { day: 1 },
      forceEventDuration: false,
      nextDayThreshold: '00:00:00',
      initialView: '',
      aspectRatio: 1.35,
      weekends: true,
      weekNumbers: false,
      weekNumberCalculation: 'local',
      editable: false,
      nowIndicator: false,
      scrollTime: '06:00:00',
      scrollTimeReset: true,
      slotMinTime: '00:00:00',
      slotMaxTime: '24:00:00',
      showNonCurrentDates: true,
      lazyFetching: true,
      startParam: 'start',
      endParam: 'end',
      timeZoneParam: 'timeZone',
      timeZone: 'local', // TODO: throw error if given falsy value?
      locales: [],
      locale: '', // blank values means it will compute based off locales[]
      dragRevertDuration: 500,
      dragScroll: true,
      allDayMaintainDuration: false,
      unselectAuto: true,
      dropAccept: '*',
      eventOrder: 'start,-duration,allDay,title',
      eventSlicing: true,
      eventPrintLayout: 'auto',
      popoverFormat: { month: 'long', day: 'numeric', year: 'numeric' },
      longPressDelay: 1000,
      eventDragMinDistance: 5, // only applies to mouse
      expandRows: false,
      navLinks: false,
      selectable: false,
      eventMinHeight: 15,
      eventMinWidth: 30,
      eventShortHeight: 30,
      monthStartFormat: { month: 'long', day: 'numeric' },
      dayCellFormat: { day: 'numeric', omitTrailing: true },
      headingLevel: 2, // like H2
      outerBorder: true,
      dayNarrowWidth: 80,
      eventOverlap: true,
      slotHeaderAlign: 'start',
      slotHeaderSticky: true,
      dayHeaderAlign: 'start',
      _dayHeaderSticky: true,
      rowEventTitleSticky: true,
      columnEventTitleSticky: true,
      nowIndicatorSnap: 'auto',
      // daygrid-only
      dayHeaders: true,
  };
  // calendar listeners
  // ------------------
  const CALENDAR_LISTENER_REFINERS = {
      datesSet: identity,
      eventsSet: identity,
      eventAdd: identity,
      eventChange: identity,
      eventRemove: identity,
      eventClick: identity, // TODO: resource for scheduler????
      eventMouseEnter: identity,
      eventMouseLeave: identity,
      select: identity, // resource for scheduler????
      unselect: identity,
      loading: identity,
      // internal
      _unmount: identity,
      _beforeprint: identity,
      _afterprint: identity,
      _noDateSelect: identity,
      _noEventDrop: identity,
      _noEventResize: identity,
      _timeScrollRequest: identity,
      // interaction-plugin-only
      dateClick: identity,
      eventDragStart: identity,
      eventDragStop: identity,
      eventDrop: identity,
      eventResizeStart: identity,
      eventResizeStop: identity,
      eventResize: identity,
      drop: identity,
      eventReceive: identity,
      eventLeave: identity,
  };
  // calendar-only options (not for view-specific)
  // ---------------------------------------------
  const CALENDAR_ONLY_OPTION_REFINERS = {
      class: refineClassNameGenerator,
      className: refineClassNameGenerator,
      viewClass: refineClassNameGenerator,
      viewDidMount: identity,
      viewWillUnmount: identity,
      views: identity,
      plugins: identity,
      initialEvents: identity,
      events: identity,
      eventSources: identity,
  };
  // view-specific options
  // ---------------------
  const VIEW_ONLY_OPTION_REFINERS = {
      type: String,
      component: identity,
      class: refineClassNameGenerator,
      className: refineClassNameGenerator,
      content: identity,
      didMount: identity,
      willUnmount: identity,
      // internal only
      buttonTextKey: String,
      dateProfileGeneratorClass: identity,
      usesMinMaxTime: Boolean,
      disallowAmbigTitle: Boolean,
  };
  const COMPLEX_OPTION_COMPARATORS = {
      // Unfortunately always need 'maybe' to handle undefined inital value, because of CalendarDataManager
      dateIncrement: isMaybePropsEqualShallow,
      headerToolbar: isMaybePropsEqualShallow,
      footerToolbar: isMaybePropsEqualShallow,
      buttons: isMaybePropsEqualDepth1,
      plugins: isMaybeArraysEqual,
      events: isMaybeArraysEqual,
      eventSources: isMaybeArraysEqual,
      ['resources']: isMaybeArraysEqual,
  };
  // util funcs
  // ----------------------------------------------------------------------------------------------------
  function refineProps(input, refiners) {
      let refined = {};
      let extra = {};
      for (let propName in refiners) {
          if (propName in input) {
              refined[propName] = refiners[propName](input[propName], propName);
          }
      }
      for (let propName in input) {
          if (!(propName in refiners)) {
              extra[propName] = input[propName];
          }
      }
      return { refined, extra };
  }
  function identity(raw) {
      return raw;
  }
  function createFalsableFormatter(input) {
      return input === false ? null : createFormatter(input);
  }

  /*
  The canonical way to construct an EventInstanceRange. Pass undefined for an edge's
  instant when the input didn't express one or the edge's marker was derived civilly —
  the property is omitted entirely (never stored as an undefined-valued key).
  */
  function buildEventInstanceRange(start, end, instantStartMs, instantEndMs) {
      const range = { start, end };
      if (instantStartMs != null) {
          range.instantStartMs = instantStartMs;
      }
      if (instantEndMs != null) {
          range.instantEndMs = instantEndMs;
      }
      return range;
  }
  // Resolves an edge to its real instant, choosing the deterministic first occurrence when
  // the marker is ambiguous and the edge does not carry an exact instant.
  function resolveEdgeInstantMs(marker, instantMs, dateEnv) {
      return instantMs ?? dateEnv.toDate(marker).valueOf();
  }
  /*
  Builds every outward-facing representation of a range edge from one policy. Exact timed
  edges use their true instant and its canonical wall-clock marker; civil/all-day edges keep
  the supplied marker and DateEnv conversion.
  */
  function buildRangeEdgeOutput(marker, instantMs, dateEnv, omitTime) {
      const canonicalMarker = instantMs != null ? dateEnv.timestampToMarker(instantMs) : marker;
      const timeZoneOffset = instantMs != null
          ? Math.round((canonicalMarker.valueOf() - instantMs) / 60000)
          : dateEnv.offsetForMarker(marker);
      if (!omitTime && instantMs != null) {
          return {
              marker: canonicalMarker,
              date: new Date(instantMs),
              dateStr: buildIsoString(canonicalMarker, timeZoneOffset),
          };
      }
      return {
          marker: canonicalMarker,
          date: dateEnv.toDate(marker),
          dateStr: omitTime
              ? dateEnv.formatIso(marker, { omitTime })
              : buildIsoString(marker, timeZoneOffset),
      };
  }
  // the exact epoch instant of a range's start: the stored instant when present, otherwise
  // deterministic first-occurrence resolution of the civil marker
  function getRangeInstantStartMs(range, dateEnv) {
      return resolveEdgeInstantMs(range.start, range.instantStartMs, dateEnv);
  }
  function getRangeInstantEndMs(range, dateEnv) {
      return resolveEdgeInstantMs(range.end, range.instantEndMs, dateEnv);
  }
  // The canonical civil end: recomputed from the exact instant for fold-compressed ranges.
  function canonicalRangeEndMarker(range, dateEnv) {
      return range.instantEndMs != null ? dateEnv.timestampToMarker(range.instantEndMs) : range.end;
  }
  function rangeHasInstants(range) {
      return range.instantStartMs != null || range.instantEndMs != null;
  }
  /*
  Like rangesIntersect, but exact: when either range carries stored instants, real instants
  are compared (a fold-compressed end's representational marker would otherwise falsely
  collide with the other occurrence's civil times). Pure-civil pairs compare markers, as before.
  */
  function instanceRangesIntersect(range0, range1, dateEnv) {
      if (rangeHasInstants(range0) || rangeHasInstants(range1)) {
          return getRangeInstantStartMs(range0, dateEnv) < getRangeInstantEndMs(range1, dateEnv) &&
              getRangeInstantEndMs(range0, dateEnv) > getRangeInstantStartMs(range1, dateEnv);
      }
      return rangesIntersect(range0, range1);
  }
  /*
  Like rangeContainsRange, but exact in the same way as instanceRangesIntersect.
  The outer range may be open-ended.
  */
  function instanceRangeContainsRange(outerRange, innerRange, dateEnv) {
      if (rangeHasInstants(outerRange) || rangeHasInstants(innerRange)) {
          const outerStartMs = outerRange.start != null ?
              resolveEdgeInstantMs(outerRange.start, outerRange.instantStartMs, dateEnv) :
              -Infinity;
          const outerEndMs = outerRange.end != null ?
              resolveEdgeInstantMs(outerRange.end, outerRange.instantEndMs, dateEnv) :
              Infinity;
          return outerStartMs <= getRangeInstantStartMs(innerRange, dateEnv) &&
              outerEndMs >= getRangeInstantEndMs(innerRange, dateEnv);
      }
      return rangeContainsRange(outerRange, innerRange);
  }
  /*
  Adds a positive duration to a start edge, deriving an END edge.
  When the edge carries an exact instant and the duration is pure clock-time, the addition
  happens in instant space (exact real elapsed time) and the result carries an instant too.
  If a fall-back fold keeps the resulting canonical marker from advancing past the edge's own
  marker, the result uses the edge's UTC-offset reading instead (the sanctioned
  instant/marker disagreement — see EventInstanceRange). Calendar-unit durations and
  instant-less edges use civil arithmetic (no instant).
  */
  function addDurationToEdge(edge, duration, dateEnv) {
      if (edge.instantMs != null && !duration.years && !duration.months && !duration.days) {
          const durMs = asRoughMs(duration);
          const instantMs = edge.instantMs + durMs;
          const marker = dateEnv.timestampToMarker(instantMs);
          return marker > edge.marker
              ? { marker, instantMs }
              : { marker: addMs(edge.marker, durMs), instantMs };
      }
      return { marker: dateEnv.add(edge.marker, duration) };
  }
  /*
  Builds a civilly-ordered EventInstanceRange from two edges, or null when the range is
  invalid: pure-civil edges are invalid unless the end marker is after the start marker;
  when either edge carries an exact instant, REAL-time order is the truth instead.
  A real range that a DST fall-back fold civilly compresses (instants ordered, markers not)
  is not discarded: its end marker is re-expressed in the start's UTC-offset reading
  (start marker + real duration), keeping the exact end instant.
  */
  function buildValidInstanceRange(start, end, dateEnv) {
      if (start.instantMs == null && end.instantMs == null) {
          return end.marker > start.marker
              ? buildEventInstanceRange(start.marker, end.marker)
              : null;
      }
      const startMs = resolveEdgeInstantMs(start.marker, start.instantMs, dateEnv);
      const endMs = resolveEdgeInstantMs(end.marker, end.instantMs, dateEnv);
      if (endMs <= startMs) {
          return null;
      }
      return buildEventInstanceRange(start.marker, end.marker > start.marker
          ? end.marker
          : addMs(start.marker, endMs - startMs), // fold-compressed: start's offset reading
      start.instantMs, end.instantMs);
  }
  function createEventInstance(defId, range) {
      return {
          instanceId: guid(),
          defId,
          range,
      };
  }

  /* Date stuff that doesn't belong in datelib core
  ----------------------------------------------------------------------------------------------------------------------*/
  // given a timed range, computes an all-day range that has the same exact duration,
  // but whose start time is aligned with the start of the day.
  function computeAlignedDayRange(timedRange) {
      let dayCnt = Math.floor(diffDays(timedRange.start, timedRange.end)) || 1;
      let start = startOfDay(timedRange.start);
      let end = addDays(start, dayCnt);
      return { start, end };
  }
  // given a timed range, computes an all-day range based on how for the end date bleeds into the next day
  // TODO: give nextDayThreshold a default arg
  function computeVisibleDayRange(timedRange, nextDayThreshold = createDuration(0)) {
      let startDay = null;
      let endDay = null;
      if (timedRange.end) {
          endDay = startOfDay(timedRange.end);
          let endTimeMS = timedRange.end.valueOf() - endDay.valueOf(); // # of milliseconds into `endDay`
          // If the end time is actually inclusively part of the next day and is equal to or
          // beyond the next day threshold, adjust the end to be the exclusive end of `endDay`.
          // Otherwise, leaving it as inclusive will cause it to exclude `endDay`.
          if (endTimeMS && endTimeMS >= asRoughMs(nextDayThreshold)) {
              endDay = addDays(endDay, 1);
          }
      }
      if (timedRange.start) {
          startDay = startOfDay(timedRange.start); // the beginning of the day the range starts
          // If end is within `startDay` but not past nextDayThreshold, assign the default duration of one day.
          if (endDay && endDay <= startDay) {
              endDay = addDays(startDay, 1);
          }
      }
      return { start: startDay, end: endDay };
  }
  function diffDates(date0, date1, dateEnv, largeUnit) {
      if (largeUnit === 'year') {
          return createDuration(dateEnv.diffWholeYears(date0, date1), 'year');
      }
      if (largeUnit === 'month') {
          return createDuration(dateEnv.diffWholeMonths(date0, date1), 'month');
      }
      return diffDayAndTime(date0, date1); // returns a duration
  }

  function parseRecurring(refined, defaultAllDay, dateEnv, recurringTypes) {
      for (let i = 0; i < recurringTypes.length; i += 1) {
          let parsed = recurringTypes[i].parse(refined, dateEnv);
          if (parsed) {
              let { allDay } = refined;
              if (allDay == null) {
                  allDay = defaultAllDay;
                  if (allDay == null) {
                      allDay = parsed.allDayGuess;
                      if (allDay == null) {
                          allDay = false;
                      }
                  }
              }
              return {
                  allDay,
                  duration: parsed.duration,
                  typeData: parsed.typeData,
                  typeId: i,
              };
          }
      }
      return null;
  }
  function expandRecurring(eventStore, framingRange, context) {
      let { dateEnv, pluginHooks, options } = context;
      let { defs, instances } = eventStore;
      // remove existing recurring instances
      // TODO: bad. always expand events as a second step
      instances = filterHash(instances, (instance) => !defs[instance.defId].recurringDef);
      for (let defId in defs) {
          let def = defs[defId];
          if (def.recurringDef) {
              let { duration } = def.recurringDef;
              if (!duration) {
                  duration = def.allDay ?
                      options.defaultAllDayEventDuration :
                      options.defaultTimedEventDuration;
              }
              let starts = expandRecurringRanges(def, duration, framingRange, dateEnv, pluginHooks.recurringTypes);
              for (let start of starts) {
                  let instance = createEventInstance(defId, {
                      start,
                      end: dateEnv.add(start, duration),
                  });
                  instances[instance.instanceId] = instance;
              }
          }
      }
      return { defs, instances };
  }
  /*
  Event MUST have a recurringDef
  */
  function expandRecurringRanges(eventDef, duration, framingRange, dateEnv, recurringTypes) {
      let typeDef = recurringTypes[eventDef.recurringDef.typeId];
      let markers = typeDef.expand(eventDef.recurringDef.typeData, {
          start: dateEnv.subtract(framingRange.start, duration), // for when event starts before framing range and goes into
          end: framingRange.end,
      }, dateEnv);
      // the recurrence plugins don't guarantee that all-day events are start-of-day, so we have to
      if (eventDef.allDay) {
          markers = markers.map(startOfDay);
      }
      return markers;
  }

  function parseEvents(rawEvents, eventSource, context, allowOpenRange, defIdMap, instanceIdMap) {
      let eventStore = createEmptyEventStore();
      let eventRefiners = buildEventRefiners(context);
      for (let rawEvent of rawEvents) {
          let tuple = parseEvent(rawEvent, eventSource, context, allowOpenRange, eventRefiners, defIdMap, instanceIdMap);
          if (tuple) {
              eventTupleToStore(tuple, eventStore);
          }
      }
      return eventStore;
  }
  function eventTupleToStore(tuple, eventStore = createEmptyEventStore()) {
      eventStore.defs[tuple.def.defId] = tuple.def;
      if (tuple.instance) {
          eventStore.instances[tuple.instance.instanceId] = tuple.instance;
      }
      return eventStore;
  }
  // retrieves events that have the same groupId as the instance specified by `instanceId`
  // or they are the same as the instance.
  // why might instanceId not be in the store? an event from another calendar?
  function getRelevantEvents(eventStore, instanceId) {
      let instance = eventStore.instances[instanceId];
      if (instance) {
          let def = eventStore.defs[instance.defId];
          // get events/instances with same group
          let newStore = filterEventStoreDefs(eventStore, (lookDef) => isEventDefsGrouped(def, lookDef));
          // add the original
          // TODO: wish we could use eventTupleToStore or something like it
          newStore.defs[def.defId] = def;
          newStore.instances[instance.instanceId] = instance;
          return newStore;
      }
      return createEmptyEventStore();
  }
  function isEventDefsGrouped(def0, def1) {
      return Boolean(def0.groupId && def0.groupId === def1.groupId);
  }
  function createEmptyEventStore() {
      return { defs: {}, instances: {} };
  }
  function mergeEventStores(store0, store1) {
      return {
          defs: { ...store0.defs, ...store1.defs },
          instances: { ...store0.instances, ...store1.instances },
      };
  }
  function filterEventStoreDefs(eventStore, filterFunc) {
      let defs = filterHash(eventStore.defs, filterFunc);
      let instances = filterHash(eventStore.instances, (instance) => (defs[instance.defId] // still exists?
      ));
      return { defs, instances };
  }
  function excludeSubEventStore(master, sub) {
      let { defs, instances } = master;
      let filteredDefs = {};
      let filteredInstances = {};
      for (let defId in defs) {
          if (!sub.defs[defId]) { // not explicitly excluded
              filteredDefs[defId] = defs[defId];
          }
      }
      for (let instanceId in instances) {
          if (!sub.instances[instanceId] && // not explicitly excluded
              filteredDefs[instances[instanceId].defId] // def wasn't filtered away
          ) {
              filteredInstances[instanceId] = instances[instanceId];
          }
      }
      return {
          defs: filteredDefs,
          instances: filteredInstances,
      };
  }

  function normalizeConstraint(input, context) {
      if (Array.isArray(input)) {
          return parseEvents(input, null, context, true); // allowOpenRange=true
      }
      if (typeof input === 'object' && input) { // non-null object
          return parseEvents([input], null, context, true); // allowOpenRange=true
      }
      if (input != null) {
          return String(input);
      }
      return null;
  }

  // TODO: better called "EventSettings" or "EventConfig"
  // TODO: move this file into structs
  // TODO: separate constraint/overlap/allow, because selection uses only that, not other props
  const EVENT_UI_REFINERS = {
      display: String,
      editable: Boolean,
      startEditable: Boolean,
      durationEditable: Boolean,
      constraint: identity, // Identity<ConstraintInput>, // circular reference. ts dies. event->constraint->event
      overlap: identity,
      allow: identity,
      class: refineClassName,
      className: refineClassName,
      color: String,
      contrastColor: String,
  };
  const EMPTY_EVENT_UI = {
      display: null,
      startEditable: null,
      durationEditable: null,
      constraints: [],
      overlap: null,
      allows: [],
      color: '',
      contrastColor: '',
      className: '',
  };
  function createEventUi(refined, context) {
      let constraint = normalizeConstraint(refined.constraint, context);
      return {
          display: refined.display || null,
          startEditable: refined.startEditable != null ? refined.startEditable : refined.editable,
          durationEditable: refined.durationEditable != null ? refined.durationEditable : refined.editable,
          constraints: constraint != null ? [constraint] : [],
          overlap: refined.overlap != null ? refined.overlap : null,
          allows: refined.allow != null ? [refined.allow] : [],
          color: refined.color || '',
          contrastColor: refined.contrastColor || '',
          className: (refined.class ?? refined.className) || '',
      };
  }
  // TODO: prevent against problems with <2 args!
  function combineEventUis(uis) {
      return uis.reduce(combineTwoEventUis, EMPTY_EVENT_UI);
  }
  function combineTwoEventUis(item0, item1) {
      return {
          display: item1.display != null ? item1.display : item0.display,
          startEditable: item1.startEditable != null ? item1.startEditable : item0.startEditable,
          durationEditable: item1.durationEditable != null ? item1.durationEditable : item0.durationEditable,
          constraints: item0.constraints.concat(item1.constraints),
          overlap: typeof item1.overlap === 'boolean' ? item1.overlap : item0.overlap,
          allows: item0.allows.concat(item1.allows),
          color: item1.color || item0.color,
          contrastColor: item1.contrastColor || item0.contrastColor,
          className: joinClassNames(item0.className, item1.className),
      };
  }

  const EVENT_NON_DATE_REFINERS = {
      id: String,
      groupId: String,
      title: String,
      url: String,
      interactive: Boolean,
  };
  const EVENT_DATE_REFINERS = {
      start: identity,
      end: identity,
      date: identity,
      allDay: Boolean,
  };
  const EVENT_REFINERS = {
      ...EVENT_NON_DATE_REFINERS,
      ...EVENT_DATE_REFINERS,
      extendedProps: identity,
  };
  function parseEvent(raw, eventSource, context, allowOpenRange, refiners = buildEventRefiners(context), defIdMap, instanceIdMap) {
      let { refined, extra } = refineEventDef(raw, context, refiners);
      let defaultAllDay = computeIsDefaultAllDay(eventSource, context);
      let recurringRes = parseRecurring(refined, defaultAllDay, context.dateEnv, context.pluginHooks.recurringTypes);
      if (recurringRes) {
          let def = parseEventDef(refined, extra, eventSource ? eventSource.sourceId : '', recurringRes.allDay, Boolean(recurringRes.duration), context, defIdMap);
          def.recurringDef = {
              typeId: recurringRes.typeId,
              typeData: recurringRes.typeData,
              duration: recurringRes.duration,
          };
          return { def, instance: null };
      }
      let singleRes = parseSingle(refined, defaultAllDay, context, allowOpenRange);
      if (singleRes) {
          let def = parseEventDef(refined, extra, eventSource ? eventSource.sourceId : '', singleRes.allDay, singleRes.hasEnd, context, defIdMap);
          let instance = createEventInstance(def.defId, singleRes.range);
          if (instanceIdMap && def.publicId && instanceIdMap[def.publicId]) {
              instance.instanceId = instanceIdMap[def.publicId];
          }
          return { def, instance };
      }
      return null;
  }
  function refineEventDef(raw, context, refiners = buildEventRefiners(context)) {
      return refineProps(raw, refiners);
  }
  function buildEventRefiners(context) {
      return { ...EVENT_UI_REFINERS, ...EVENT_REFINERS, ...context.pluginHooks.eventRefiners };
  }
  /*
  Will NOT populate extendedProps with the leftover properties.
  Will NOT populate date-related props.
  */
  function parseEventDef(refined, extra, sourceId, allDay, hasEnd, context, defIdMap) {
      let def = {
          title: refined.title || '',
          groupId: refined.groupId || '',
          publicId: refined.id || '',
          url: refined.url || '',
          recurringDef: null,
          defId: ((defIdMap && refined.id) ? defIdMap[refined.id] : '') || guid(),
          sourceId,
          allDay,
          hasEnd,
          interactive: refined.interactive,
          ui: createEventUi(refined, context),
          extendedProps: {
              ...(refined.extendedProps || {}),
              ...extra,
          },
      };
      for (let memberAdder of context.pluginHooks.eventDefMemberAdders) {
          Object.assign(def, memberAdder(refined));
      }
      // help out EventImpl from having user modify props
      Object.freeze(def.ui.className); // might be simple string, but freeze still works
      Object.freeze(def.extendedProps);
      return def;
  }
  function parseSingle(refined, defaultAllDay, context, allowOpenRange) {
      let { allDay } = refined;
      let startMeta;
      let startMarker = null;
      let hasEnd = false;
      let endMeta;
      let endMarker = null;
      let startInput = refined.start != null ? refined.start : refined.date;
      startMeta = context.dateEnv.createMarkerMeta(startInput);
      if (startMeta) {
          startMarker = startMeta.marker;
      }
      else if (!allowOpenRange) {
          return null;
      }
      if (refined.end != null) {
          endMeta = context.dateEnv.createMarkerMeta(refined.end);
      }
      if (allDay == null) {
          if (defaultAllDay != null) {
              allDay = defaultAllDay;
          }
          else {
              // fall back to the date props LAST
              allDay = (!startMeta || startMeta.isTimeUnspecified) &&
                  (!endMeta || endMeta.isTimeUnspecified);
          }
      }
      if (allDay && startMarker) {
          startMarker = startOfDay(startMarker);
      }
      // exact instants are stamped when the input expressed them (ISO with offset, Date,
      // epoch ms) and the marker was used as-is. allDay truncation invalidates instants.
      let startInstantMs = (!allDay && startMeta) ? startMeta.instantMs : undefined;
      let range = null;
      if (endMeta) {
          endMarker = allDay ? startOfDay(endMeta.marker) : endMeta.marker;
          if (!startMarker) { // open start (allowOpenRange)
              range = buildEventInstanceRange(startMarker, endMarker, undefined, allDay ? undefined : endMeta.instantMs);
          }
          else if (allDay) {
              if (endMarker > startMarker) {
                  range = buildEventInstanceRange(startMarker, endMarker);
              }
          }
          else {
              // rejects ends invalid in real time; real ranges that a DST fall-back fold civilly
              // compresses keep their exact end, re-expressed in the start's offset reading
              range = buildValidInstanceRange({ marker: startMarker, instantMs: startInstantMs }, { marker: endMarker, instantMs: endMeta.instantMs }, context.dateEnv);
          }
      }
      if (range) {
          hasEnd = true;
      }
      else if (allowOpenRange) {
          range = buildEventInstanceRange(startMarker, null, startInstantMs);
      }
      else {
          hasEnd = context.options.forceEventDuration || false;
          // exact starts get an exact derived end (real elapsed duration), so the end can't
          // re-resolve to the wrong side of a DST fold
          let endEdge = addDurationToEdge({ marker: startMarker, instantMs: startInstantMs }, allDay ?
              context.options.defaultAllDayEventDuration :
              context.options.defaultTimedEventDuration, context.dateEnv);
          range = buildEventInstanceRange(startMarker, endEdge.marker, startInstantMs, endEdge.instantMs);
      }
      return { allDay, hasEnd, range };
  }
  function computeIsDefaultAllDay(eventSource, context) {
      let res = null;
      if (eventSource) {
          res = eventSource.defaultAllDay;
      }
      if (res == null) {
          res = context.options.defaultAllDay;
      }
      return res;
  }

  const STANDARD_PROPS = {
      start: identity,
      end: identity,
      allDay: Boolean,
  };
  function parseDateSpan(raw, dateEnv, defaultDuration) {
      let span = parseOpenDateSpan(raw, dateEnv);
      if (!span) {
          return null;
      }
      let { range } = span;
      if (!range.start) {
          return null;
      }
      if (!range.end) {
          if (defaultDuration == null) {
              return null;
          }
          const endEdge = addDurationToEdge({ marker: range.start, instantMs: span.instantStartMs }, defaultDuration, dateEnv);
          range.end = endEdge.marker;
          if (endEdge.instantMs != null) {
              span.instantEndMs = endEdge.instantMs;
          }
      }
      return span;
  }
  /*
  TODO: somehow combine with parseRange?
  Will return null if the start/end props were present but parsed invalidly.
  */
  function parseOpenDateSpan(raw, dateEnv) {
      let { refined: standardProps, extra } = refineProps(raw, STANDARD_PROPS);
      let startMeta = standardProps.start ? dateEnv.createMarkerMeta(standardProps.start) : null;
      let endMeta = standardProps.end ? dateEnv.createMarkerMeta(standardProps.end) : null;
      let { allDay } = standardProps;
      if (allDay == null) {
          allDay = (startMeta && startMeta.isTimeUnspecified) &&
              (!endMeta || endMeta.isTimeUnspecified);
      }
      let range = {
          start: startMeta ? startMeta.marker : null,
          end: endMeta ? endMeta.marker : null,
      };
      if (!allDay && startMeta && endMeta && (startMeta.instantMs != null || endMeta.instantMs != null)) {
          const validRange = buildValidInstanceRange({ marker: startMeta.marker, instantMs: startMeta.instantMs }, { marker: endMeta.marker, instantMs: endMeta.instantMs }, dateEnv);
          if (!validRange && startMeta.instantMs != null && endMeta.instantMs != null) {
              return null;
          }
          if (validRange) {
              range = { start: validRange.start, end: validRange.end };
          }
      }
      const span = {
          range,
          allDay,
          ...extra,
      };
      if (allDay) {
          delete span.instantStartMs;
          delete span.instantEndMs;
      }
      else {
          if (startMeta?.instantMs != null) {
              span.instantStartMs = startMeta.instantMs;
          }
          if (endMeta?.instantMs != null) {
              span.instantEndMs = endMeta.instantMs;
          }
      }
      return span;
  }
  function isDateSpansEqual(span0, span1) {
      return rangesEqual(span0.range, span1.range) &&
          span0.allDay === span1.allDay &&
          isSpanPropsEqual(span0, span1);
  }
  // the NON-DATE-RELATED props
  function isSpanPropsEqual(span0, span1) {
      for (let propName in span1) {
          if (propName !== 'range' && propName !== 'allDay') {
              if (span0[propName] !== span1[propName]) {
                  return false;
              }
          }
      }
      // are there any props that span0 has that span1 DOESN'T have?
      // both have range/allDay, so no need to special-case.
      for (let propName in span0) {
          if (!(propName in span1)) {
              return false;
          }
      }
      return true;
  }
  function buildDateSpanApi(span, dateEnv) {
      return {
          ...buildRangeApi(span.range, dateEnv, span.allDay, span),
          allDay: span.allDay,
      };
  }
  function buildRangeApiWithTimeZone(range, dateEnv, omitTime) {
      return {
          ...buildRangeApi(range, dateEnv, omitTime),
          timeZone: dateEnv.timeZone,
      };
  }
  function buildRangeApi(range, dateEnv, omitTime, rangeMeta) {
      // exact instants may ride on a span (rangeMeta) or on the range itself
      const instantStartMs = rangeMeta?.instantStartMs ?? range.instantStartMs;
      const instantEndMs = rangeMeta?.instantEndMs ?? range.instantEndMs;
      const start = buildRangeEdgeOutput(range.start, instantStartMs, dateEnv, omitTime);
      const end = buildRangeEdgeOutput(range.end, instantEndMs, dateEnv, omitTime);
      return {
          start: start.date,
          end: end.date,
          startStr: start.dateStr,
          endStr: end.dateStr,
      };
  }
  function getDateSpanInstantStartMs(dateSpan, dateEnv) {
      return resolveEdgeInstantMs(dateSpan.range.start, dateSpan.instantStartMs, dateEnv);
  }
  function getDateSpanInstantEndMs(dateSpan, dateEnv) {
      return resolveEdgeInstantMs(dateSpan.range.end, dateSpan.instantEndMs, dateEnv);
  }
  function fabricateEventRange(dateSpan, eventUiBases, context) {
      let res = refineEventDef({ editable: false }, context);
      let def = parseEventDef(res.refined, res.extra, '', // sourceId
      dateSpan.allDay, true, // hasEnd
      context);
      return {
          def,
          ui: compileEventUi(def, eventUiBases),
          instance: createEventInstance(def.defId, dateSpan.range),
          range: dateSpan.range,
          isStart: true,
          isEnd: true,
      };
  }

  function triggerDateSelect(selection, pev, context) {
      context.emitter.trigger('select', {
          ...buildDateSpanApiWithContext(selection, context),
          jsEvent: pev ? pev.origEvent : null, // Is this always a mouse event? See #4655
          view: context.viewApi || context.calendarApi.view,
      });
  }
  function triggerDateUnselect(pev, context) {
      context.emitter.trigger('unselect', {
          jsEvent: pev ? pev.origEvent : null, // Is this always a mouse event? See #4655
          view: context.viewApi || context.calendarApi.view,
      });
  }
  function buildDateSpanApiWithContext(dateSpan, context) {
      let props = {};
      for (let transform of context.pluginHooks.dateSpanTransforms) {
          Object.assign(props, transform(dateSpan, context));
      }
      Object.assign(props, buildDateSpanApi(dateSpan, context.dateEnv));
      return props;
  }
  // Given an event's allDay status and start date, return what its fallback end date should be.
  // TODO: rename to computeDefaultEventEnd
  function getDefaultEventEnd(allDay, marker, context) {
      let { dateEnv, options } = context;
      let end = marker;
      if (allDay) {
          end = startOfDay(end);
          end = dateEnv.add(end, options.defaultAllDayEventDuration);
      }
      else {
          end = dateEnv.add(end, options.defaultTimedEventDuration);
      }
      return end;
  }
  // like getDefaultEventEnd, but edge-based: an exact start yields an exact derived end
  // (real elapsed duration), so the end can't re-resolve to the wrong side of a DST fold
  function getDefaultEventEndEdge(allDay, start, context) {
      if (allDay) {
          return { marker: getDefaultEventEnd(true, start.marker, context) };
      }
      return addDurationToEdge(start, context.options.defaultTimedEventDuration, context.dateEnv);
  }

  // applies the mutation to ALL defs/instances within the event store
  function applyMutationToEventStore(eventStore, eventConfigBase, mutation, context) {
      let eventConfigs = compileEventUis(eventStore.defs, eventConfigBase);
      let dest = createEmptyEventStore();
      for (let defId in eventStore.defs) {
          let def = eventStore.defs[defId];
          dest.defs[defId] = applyMutationToEventDef(def, eventConfigs[defId], mutation, context);
      }
      for (let instanceId in eventStore.instances) {
          let instance = eventStore.instances[instanceId];
          let def = dest.defs[instance.defId]; // important to grab the newly modified def
          dest.instances[instanceId] = applyMutationToEventInstance(instance, def, eventConfigs[instance.defId], mutation, context);
      }
      return dest;
  }
  function applyMutationToEventDef(eventDef, eventConfig, mutation, context) {
      let standardProps = mutation.standardProps || {};
      // if hasEnd has not been specified, guess a good value based on deltas.
      // if duration will change, there's no way the default duration will persist,
      // and thus, we need to mark the event as having a real end
      if (standardProps.hasEnd == null &&
          eventConfig.durationEditable &&
          (mutation.startDelta || mutation.endDelta)) {
          standardProps.hasEnd = true; // TODO: is this mutation okay?
      }
      let copy = {
          ...eventDef,
          ...standardProps,
          ui: { ...eventDef.ui, ...standardProps.ui }, // the only prop we want to recursively overlay
      };
      if (mutation.extendedProps) {
          copy.extendedProps = { ...copy.extendedProps, ...mutation.extendedProps };
      }
      for (let applier of context.pluginHooks.eventDefMutationAppliers) {
          applier(copy, mutation, context);
      }
      if (!copy.hasEnd && context.options.forceEventDuration) {
          copy.hasEnd = true;
      }
      return copy;
  }
  function applyMutationToEventInstance(eventInstance, eventDef, // must first be modified by applyMutationToEventDef
  eventConfig, mutation, context) {
      let forceAllDay = mutation.standardProps && mutation.standardProps.allDay === true;
      let clearEnd = mutation.standardProps && mutation.standardProps.hasEnd === false;
      let copy = { ...eventInstance };
      if (forceAllDay) {
          copy.range = computeAlignedDayRange(copy.range); // fresh plain range: instants stripped
      }
      if (mutation.datesDelta && eventConfig.startEditable) {
          copy.range = buildInstanceRange(addDeltaToRangeEdge(copy.range.start, copy.range.instantStartMs, mutation.datesDelta, mutation.instantDatesDeltaMs, context), addDeltaToRangeEdge(copy.range.end, copy.range.instantEndMs, mutation.datesDelta, mutation.instantDatesDeltaMs, context));
      }
      if (mutation.startDelta && eventConfig.durationEditable) {
          copy.range = buildInstanceRange(addDeltaToRangeEdge(copy.range.start, copy.range.instantStartMs, mutation.startDelta, mutation.instantStartDeltaMs, context), { marker: copy.range.end, instantMs: copy.range.instantEndMs });
      }
      if (mutation.endDelta && eventConfig.durationEditable) {
          copy.range = buildInstanceRange({ marker: copy.range.start, instantMs: copy.range.instantStartMs }, addDeltaToRangeEdge(copy.range.end, copy.range.instantEndMs, mutation.endDelta, mutation.instantEndDeltaMs, context));
      }
      if (clearEnd) {
          const startEdge = { marker: copy.range.start, instantMs: copy.range.instantStartMs };
          copy.range = buildInstanceRange(startEdge, getDefaultEventEndEdge(eventDef.allDay, startEdge, context));
      }
      // in case event was all-day but the supplied deltas were not
      // better util for this?
      if (eventDef.allDay) {
          copy.range = {
              start: startOfDay(copy.range.start),
              end: startOfDay(copy.range.end),
          };
      }
      // handle invalid durations. a timed range can be invalid civilly or in real time.
      // a real range that a DST fall-back fold civilly compresses is re-expressed (end in the
      // start's offset reading) rather than repaired away
      if (eventDef.allDay) {
          if (copy.range.end <= copy.range.start) {
              const startEdge = { marker: copy.range.start };
              copy.range = buildInstanceRange(startEdge, getDefaultEventEndEdge(true, startEdge, context));
          }
      }
      else {
          const startEdge = { marker: copy.range.start, instantMs: copy.range.instantStartMs };
          copy.range = buildValidInstanceRange(startEdge, { marker: copy.range.end, instantMs: copy.range.instantEndMs }, context.dateEnv) ?? buildInstanceRange(startEdge, getDefaultEventEndEdge(false, startEdge, context));
      }
      return copy;
  }
  /*
  When instantDeltaMs is given, moves the edge by an exact instant amount, basing off the
  edge's stored instant when present (preserves identity through DST fall-back doubled times).
  The resulting marker is always a real local time in the current timeZone; ambiguous civil
  times resolve deterministically. Civil (Duration-only) deltas invalidate any stored instant.
  */
  function addDeltaToRangeEdge(marker, instantMs, delta, instantDeltaMs, context) {
      if (instantDeltaMs != null) {
          const newInstantMs = resolveEdgeInstantMs(marker, instantMs, context.dateEnv) + instantDeltaMs;
          return {
              marker: context.dateEnv.timestampToMarker(newInstantMs),
              instantMs: newInstantMs,
          };
      }
      // civil deltas apply to the edge's canonical civil form — a fold-compressed end's
      // stored marker is representational and must not enter civil arithmetic
      return {
          marker: context.dateEnv.add(instantMs != null ? context.dateEnv.timestampToMarker(instantMs) : marker, delta),
      };
  }
  function buildInstanceRange(start, end) {
      return buildEventInstanceRange(start.marker, end.marker, start.instantMs, end.instantMs);
  }

  class EventSourceImpl {
      constructor(context, internalEventSource) {
          this.context = context;
          this.internalEventSource = internalEventSource;
      }
      remove() {
          this.context.dispatch({
              type: 'REMOVE_EVENT_SOURCE',
              sourceId: this.internalEventSource.sourceId,
          });
      }
      refetch() {
          this.context.dispatch({
              type: 'FETCH_EVENT_SOURCES',
              sourceIds: [this.internalEventSource.sourceId],
              isRefetch: true,
          });
      }
      get id() {
          return this.internalEventSource.publicId;
      }
      get url() {
          return this.internalEventSource.meta.url;
      }
      get format() {
          return this.internalEventSource.meta.format; // TODO: bad. not guaranteed
      }
  }

  class EventImpl {
      // instance will be null if expressing a recurring event that has no current instances,
      // OR if trying to validate an incoming external event that has no dates assigned
      constructor(context, def, instance) {
          this._context = context;
          this._def = def;
          this._instance = instance || null;
      }
      /*
      TODO: make event struct more responsible for this
      */
      setProp(name, val) {
          if (name in EVENT_DATE_REFINERS) {
              warn(`Cannot set date-related event property \`${name}\`. Use a method instead.`);
              // TODO: make proper aliasing system?
          }
          else if (name === 'id') {
              val = EVENT_NON_DATE_REFINERS[name](val);
              this.mutate({
                  standardProps: { publicId: val }, // hardcoded internal name
              });
          }
          else if (name in EVENT_NON_DATE_REFINERS) {
              val = EVENT_NON_DATE_REFINERS[name](val);
              this.mutate({
                  standardProps: { [name]: val },
              });
          }
          else if (name in EVENT_UI_REFINERS) {
              let ui = EVENT_UI_REFINERS[name](val);
              if (name === 'editable') {
                  ui = { startEditable: val, durationEditable: val };
              }
              else {
                  ui = { [name]: val };
              }
              this.mutate({
                  standardProps: { ui },
              });
          }
          else {
              warn(`Cannot set event property \`${name}\`. Use setExtendedProp instead.`);
          }
      }
      setExtendedProp(name, val) {
          this.mutate({
              extendedProps: { [name]: val },
          });
      }
      setStart(startInput, options = {}) {
          let { dateEnv } = this._context;
          let startMeta = dateEnv.createMarkerMeta(startInput);
          if (startMeta && this._instance) { // TODO: warning if parsed bad
              let instanceRange = this._instance.range;
              let startDelta = diffDates(instanceRange.start, startMeta.marker, dateEnv, options.granularity); // what if parsed bad!?
              let instantDeltaMs = computeInstantDeltaMs(startMeta, getRangeInstantStartMs(instanceRange, dateEnv), options.granularity);
              if (options.maintainDuration) {
                  this.mutate({ datesDelta: startDelta, instantDatesDeltaMs: instantDeltaMs });
              }
              else {
                  this.mutate({ startDelta, instantStartDeltaMs: instantDeltaMs });
              }
          }
      }
      setEnd(endInput, options = {}) {
          let { dateEnv } = this._context;
          let endMeta = null;
          if (endInput != null) {
              endMeta = dateEnv.createMarkerMeta(endInput);
              if (!endMeta) {
                  return; // TODO: warning if parsed bad
              }
          }
          if (this._instance) {
              if (endMeta) {
                  let instanceRange = this._instance.range;
                  // canonical base: matches what a civil delta will be applied to
                  let endDelta = diffDates(canonicalRangeEndMarker(instanceRange, dateEnv), endMeta.marker, dateEnv, options.granularity);
                  let instantDeltaMs = computeInstantDeltaMs(endMeta, getRangeInstantEndMs(instanceRange, dateEnv), options.granularity);
                  this.mutate({ endDelta, instantEndDeltaMs: instantDeltaMs });
              }
              else {
                  this.mutate({ standardProps: { hasEnd: false } });
              }
          }
      }
      setDates(startInput, endInput, options = {}) {
          let { dateEnv } = this._context;
          let standardProps = { allDay: options.allDay };
          let startMeta = dateEnv.createMarkerMeta(startInput);
          let endMeta = null;
          if (!startMeta) {
              return; // TODO: warning if parsed bad
          }
          if (endInput != null) {
              endMeta = dateEnv.createMarkerMeta(endInput);
              if (!endMeta) { // TODO: warning if parsed bad
                  return;
              }
          }
          if (this._instance) {
              let instanceRange = this._instance.range;
              // converting to all-day is civil-only: exact instants don't survive day-alignment
              let skipInstants = options.allDay === true;
              let instantStartDeltaMs = skipInstants ? undefined : computeInstantDeltaMs(startMeta, getRangeInstantStartMs(instanceRange, dateEnv), options.granularity);
              let instantEndDeltaMs = (skipInstants || !endMeta) ? undefined : computeInstantDeltaMs(endMeta, getRangeInstantEndMs(instanceRange, dateEnv), options.granularity);
              // when computing the diff for an event being converted to all-day,
              // compute diff off of the all-day values the way event-mutation does.
              if (options.allDay === true) {
                  instanceRange = computeAlignedDayRange(instanceRange);
              }
              // canonical bases: match what civil deltas will be applied to
              let startDelta = diffDates(instanceRange.start, startMeta.marker, dateEnv, options.granularity);
              if (endMeta) {
                  let endDelta = diffDates(canonicalRangeEndMarker(instanceRange, dateEnv), endMeta.marker, dateEnv, options.granularity);
                  if (durationsEqual(startDelta, endDelta) && instantStartDeltaMs === instantEndDeltaMs) {
                      this.mutate({ datesDelta: startDelta, instantDatesDeltaMs: instantStartDeltaMs, standardProps });
                  }
                  else {
                      this.mutate({ startDelta, endDelta, instantStartDeltaMs, instantEndDeltaMs, standardProps });
                  }
              }
              else { // means "clear the end"
                  standardProps.hasEnd = false;
                  this.mutate({ datesDelta: startDelta, instantDatesDeltaMs: instantStartDeltaMs, standardProps });
              }
          }
      }
      moveStart(deltaInput) {
          let delta = createDuration(deltaInput);
          if (delta) { // TODO: warning if parsed bad
              this.mutate({ startDelta: delta });
          }
      }
      moveEnd(deltaInput) {
          let delta = createDuration(deltaInput);
          if (delta) { // TODO: warning if parsed bad
              this.mutate({ endDelta: delta });
          }
      }
      moveDates(deltaInput) {
          let delta = createDuration(deltaInput);
          if (delta) { // TODO: warning if parsed bad
              this.mutate({ datesDelta: delta });
          }
      }
      setAllDay(allDay, options = {}) {
          let standardProps = { allDay };
          let { maintainDuration } = options;
          if (maintainDuration == null) {
              maintainDuration = this._context.options.allDayMaintainDuration;
          }
          if (this._def.allDay !== allDay) {
              standardProps.hasEnd = maintainDuration;
          }
          this.mutate({ standardProps });
      }
      formatRange(formatInput) {
          let { dateEnv } = this._context;
          let instance = this._instance;
          let formatter = createFormatter(formatInput);
          let start = buildRangeEdgeOutput(instance.range.start, instance.range.instantStartMs, dateEnv);
          if (this._def.hasEnd) {
              let end = buildRangeEdgeOutput(instance.range.end, instance.range.instantEndMs, dateEnv);
              return joinDateTimeFormatParts(dateEnv.formatRangeToParts(start.marker, end.marker, formatter, {
                  startInstantMs: start.date.valueOf(),
                  endInstantMs: end.date.valueOf(),
              }));
          }
          return joinDateTimeFormatParts(dateEnv.formatToParts(start.marker, formatter, {
              instantMs: start.date.valueOf(),
          }));
      }
      mutate(mutation) {
          let instance = this._instance;
          if (instance) {
              let def = this._def;
              let context = this._context;
              let { eventStore } = context.getCurrentData();
              let relevantEvents = getRelevantEvents(eventStore, instance.instanceId);
              let eventConfigBase = {
                  '': {
                      display: '',
                      startEditable: true,
                      durationEditable: true,
                      constraints: [],
                      overlap: null,
                      allows: [],
                      color: '',
                      contrastColor: '',
                      className: '',
                  },
              };
              relevantEvents = applyMutationToEventStore(relevantEvents, eventConfigBase, mutation, context);
              let oldEvent = new EventImpl(context, def, instance); // snapshot
              this._def = relevantEvents.defs[def.defId];
              this._instance = relevantEvents.instances[instance.instanceId];
              context.dispatch({
                  type: 'MERGE_EVENTS',
                  eventStore: relevantEvents,
              });
              context.emitter.trigger('eventChange', {
                  oldEvent,
                  event: this,
                  relatedEvents: buildEventApis(relevantEvents, context, instance),
                  revert() {
                      context.dispatch({
                          type: 'RESET_EVENTS',
                          eventStore, // the ORIGINAL store
                      });
                  },
              });
          }
      }
      remove() {
          let context = this._context;
          let asStore = eventApiToStore(this);
          context.dispatch({
              type: 'REMOVE_EVENTS',
              eventStore: asStore,
          });
          context.emitter.trigger('eventRemove', {
              event: this,
              relatedEvents: [],
              revert() {
                  context.dispatch({
                      type: 'MERGE_EVENTS',
                      eventStore: asStore,
                  });
              },
          });
      }
      get source() {
          let { sourceId } = this._def;
          if (sourceId) {
              return new EventSourceImpl(this._context, this._context.getCurrentData().eventSources[sourceId]);
          }
          return null;
      }
      get start() {
          let instance = this._instance;
          if (instance) {
              return buildRangeEdgeOutput(instance.range.start, instance.range.instantStartMs, this._context.dateEnv, this._def.allDay).date;
          }
          return null;
      }
      get end() {
          let instance = this._instance;
          if (instance && this._def.hasEnd) {
              return buildRangeEdgeOutput(instance.range.end, instance.range.instantEndMs, this._context.dateEnv, this._def.allDay).date;
          }
          return null;
      }
      get startStr() {
          let instance = this._instance;
          if (instance) {
              return buildRangeEdgeOutput(instance.range.start, instance.range.instantStartMs, this._context.dateEnv, this._def.allDay).dateStr;
          }
          return '';
      }
      get endStr() {
          let instance = this._instance;
          if (instance && this._def.hasEnd) {
              return buildRangeEdgeOutput(instance.range.end, instance.range.instantEndMs, this._context.dateEnv, this._def.allDay).dateStr;
          }
          return '';
      }
      // computable props that all access the def
      // TODO: find a TypeScript-compatible way to do this at scale
      get id() { return this._def.publicId; }
      get groupId() { return this._def.groupId; }
      get allDay() { return this._def.allDay; }
      get title() { return this._def.title; }
      get url() { return this._def.url; }
      get display() { return this._def.ui.display || 'auto'; } // bad. just normalize the type earlier
      get startEditable() { return this._def.ui.startEditable; }
      get durationEditable() { return this._def.ui.durationEditable; }
      get constraint() { return this._def.ui.constraints[0] || null; }
      get overlap() { return this._def.ui.overlap; }
      get allow() { return this._def.ui.allows[0] || null; }
      get color() { return this._def.ui.color; }
      get contrastColor() { return this._def.ui.contrastColor; }
      // NOTE: user can't modify these because Object.freeze was called in event-def parsing
      get className() { return this._def.ui.className; }
      get extendedProps() { return this._def.extendedProps; }
      toPlainObject(settings = {}) {
          let def = this._def;
          let { ui } = def;
          let { startStr, endStr } = this;
          let res = {
              allDay: def.allDay,
          };
          if (def.title) {
              res.title = def.title;
          }
          if (startStr) {
              res.start = startStr;
          }
          if (endStr) {
              res.end = endStr;
          }
          if (def.publicId) {
              res.id = def.publicId;
          }
          if (def.groupId) {
              res.groupId = def.groupId;
          }
          if (def.url) {
              res.url = def.url;
          }
          if (ui.display && ui.display !== 'auto') {
              res.display = ui.display;
          }
          // TODO: what about recurring-event properties???
          // TODO: include startEditable/durationEditable/constraint/overlap/allow
          if (ui.color) {
              res.color = ui.color;
          }
          if (ui.contrastColor) {
              res.contrastColor = ui.contrastColor;
          }
          if (ui.className) {
              res.className = ui.className;
          }
          if (Object.keys(def.extendedProps).length) {
              if (settings.collapseExtendedProps) {
                  Object.assign(res, def.extendedProps);
              }
              else {
                  res.extendedProps = def.extendedProps;
              }
          }
          return res;
      }
      toJSON() {
          return this.toPlainObject();
      }
  }
  /*
  The exact-ms counterpart of a civil delta, present when the input expressed an exact
  instant (ISO with offset, Date, epoch ms). Undefined means the mutation applies only the
  civil delta. Skipped when a granularity is requested (whole-unit semantics).
  */
  function computeInstantDeltaMs(meta, fromInstantMs, granularity) {
      return (meta.instantMs != null && !granularity)
          ? meta.instantMs - fromInstantMs
          : undefined;
  }
  function eventApiToStore(eventApi) {
      let def = eventApi._def;
      let instance = eventApi._instance;
      return {
          defs: { [def.defId]: def },
          instances: instance
              ? { [instance.instanceId]: instance }
              : {},
      };
  }
  function buildEventApis(eventStore, context, excludeInstance) {
      let { defs, instances } = eventStore;
      let eventApis = [];
      let excludeInstanceId = excludeInstance ? excludeInstance.instanceId : '';
      for (let id in instances) {
          let instance = instances[id];
          let def = defs[instance.defId];
          if (instance.instanceId !== excludeInstanceId) {
              eventApis.push(new EventImpl(context, def, instance));
          }
      }
      return eventApis;
  }

  /*
  Specifying nextDayThreshold signals that all-day ranges should be sliced.
  */
  function sliceEventStore(eventStore, eventUiBases, framingRange, nextDayThreshold) {
      let inverseBgByGroupId = {};
      let inverseBgByDefId = {};
      let defByGroupId = {};
      let bgRanges = [];
      let fgRanges = [];
      let eventUis = compileEventUis(eventStore.defs, eventUiBases);
      for (let defId in eventStore.defs) {
          let def = eventStore.defs[defId];
          let ui = eventUis[def.defId];
          if (ui.display === 'inverse-background') {
              if (def.groupId) {
                  inverseBgByGroupId[def.groupId] = [];
                  if (!defByGroupId[def.groupId]) {
                      defByGroupId[def.groupId] = def;
                  }
              }
              else {
                  inverseBgByDefId[defId] = [];
              }
          }
      }
      for (let instanceId in eventStore.instances) {
          let instance = eventStore.instances[instanceId];
          let def = eventStore.defs[instance.defId];
          let ui = eventUis[def.defId];
          let origRange = instance.range;
          let normalRange = (!def.allDay && nextDayThreshold) ?
              computeVisibleDayRange(origRange, nextDayThreshold) :
              origRange;
          let slicedRange = intersectRanges(normalRange, framingRange);
          if (slicedRange) {
              if (ui.display === 'inverse-background') {
                  if (def.groupId) {
                      inverseBgByGroupId[def.groupId].push(slicedRange);
                  }
                  else {
                      inverseBgByDefId[instance.defId].push(slicedRange);
                  }
              }
              else if (ui.display !== 'none') {
                  (ui.display === 'background' ? bgRanges : fgRanges).push({
                      def,
                      ui,
                      instance,
                      range: buildSlicedEventRange(origRange, normalRange, slicedRange),
                      isStart: normalRange.start && normalRange.start.valueOf() === slicedRange.start.valueOf(),
                      isEnd: normalRange.end && normalRange.end.valueOf() === slicedRange.end.valueOf(),
                  });
              }
          }
      }
      for (let groupId in inverseBgByGroupId) { // BY GROUP
          let ranges = inverseBgByGroupId[groupId];
          let invertedRanges = invertRanges(ranges, framingRange);
          for (let invertedRange of invertedRanges) {
              let def = defByGroupId[groupId];
              let ui = eventUis[def.defId];
              bgRanges.push({
                  def,
                  ui,
                  instance: null,
                  range: invertedRange,
                  isStart: false,
                  isEnd: false,
              });
          }
      }
      for (let defId in inverseBgByDefId) {
          let ranges = inverseBgByDefId[defId];
          let invertedRanges = invertRanges(ranges, framingRange);
          for (let invertedRange of invertedRanges) {
              bgRanges.push({
                  def: eventStore.defs[defId],
                  ui: eventUis[defId],
                  instance: null,
                  range: invertedRange,
                  isStart: false,
                  isEnd: false,
              });
          }
      }
      return { bg: bgRanges, fg: fgRanges };
  }
  /*
  Carries instant fields from the original event range onto the sliced range, per-edge, only
  for edges that were not clipped by the framing range. Only applies when the range was not
  day-normalized (normalRange === origRange, i.e. timed events not subject to nextDayThreshold).
  */
  function buildSlicedEventRange(origRange, normalRange, slicedRange) {
      if (normalRange !== origRange) {
          return slicedRange;
      }
      return buildEventInstanceRange(slicedRange.start, slicedRange.end, slicedRange.start.valueOf() === origRange.start.valueOf() ? origRange.instantStartMs : undefined, slicedRange.end.valueOf() === origRange.end.valueOf() ? origRange.instantEndMs : undefined);
  }
  function hasBgRendering(def) {
      return def.ui.display === 'background' || def.ui.display === 'inverse-background';
  }
  function setElEventRange(el, eventRange) {
      el.fcEventRange = eventRange;
  }
  function getElEventRange(el) {
      return el.fcEventRange ||
          el.parentNode.fcEventRange || // for the harness
          null;
  }
  // event ui computation
  function compileEventUis(eventDefs, eventUiBases) {
      return mapHash(eventDefs, (eventDef) => compileEventUi(eventDef, eventUiBases));
  }
  /*
  I wish we didn't need to deal with inheritance of all properties all together
  I wish you could resolve just eventDisplay first, then the others
  */
  function compileEventUi(eventDef, eventUiBases) {
      const uis = [];
      const fallbackBase = eventUiBases[''];
      const defBase = eventUiBases[eventDef.defId];
      if (fallbackBase) {
          uis.push(fallbackBase);
      }
      if (defBase) {
          uis.push(defBase);
      }
      uis.push(eventDef.ui);
      return combineEventUis(uis);
  }
  function sortEventSegs(segs, eventOrderSpecs) {
      let objs = segs.map(buildSegCompareObj);
      objs.sort((obj0, obj1) => compareByFieldSpecs(obj0, obj1, eventOrderSpecs)); // !!!
      return objs.map((c) => c._seg);
  }
  // returns a object with all primitive props that can be compared
  function buildSegCompareObj(seg) {
      let { eventRange } = seg;
      let eventDef = eventRange.def;
      let range = eventRange.instance ? eventRange.instance.range : eventRange.range;
      let start = range.start ? range.start.valueOf() : 0; // TODO: better support for open-range events
      let end = range.end ? range.end.valueOf() : 0; // "
      return {
          ...eventDef.extendedProps,
          ...eventDef,
          id: eventDef.publicId,
          start,
          end,
          duration: end - start,
          allDay: Number(eventDef.allDay),
          _seg: seg, // for later retrieval
      };
  }
  function computeEventRangeDraggable(eventRange, context) {
      let { pluginHooks } = context;
      let transformers = pluginHooks.isDraggableTransformers;
      let { def, ui } = eventRange;
      let val = ui.startEditable;
      for (let transformer of transformers) {
          val = transformer(val, def, ui, context);
      }
      return val;
  }
  /*
  slicedStart/slicedEnd are optionally supplied to signal where breaks occur in view-specific segment
  a better approach is to always slice with dates and always supply this argument,
  however, daygrid only slices by row/col
  */
  function buildEventRangeTimeText(timeFormat, eventRange, // timed/whole-day span
  slicedStart, // view-sliced timed/whole-day span
  slicedEnd, // view-sliced timed/whole-day span
  isStart, isEnd, context, defaultDisplayEventTime = true, defaultDisplayEventEnd = true) {
      const { dateEnv, options } = context;
      const { def } = eventRange;
      const { range } = eventRange.instance;
      const canonicalStart = buildRangeEdgeOutput(range.start, range.instantStartMs, dateEnv);
      const canonicalEnd = buildRangeEdgeOutput(range.end, range.instantEndMs, dateEnv);
      let { displayEventTime, displayEventEnd } = options;
      if (displayEventTime == null) {
          displayEventTime = defaultDisplayEventTime !== false;
      }
      if (displayEventEnd == null) {
          displayEventEnd = defaultDisplayEventEnd !== false;
      }
      const startDate = (!isStart &&
          slicedStart &&
          // if seg is the first seg, but start-date cut-off by slotMinTime, (technically isStart=false)
          // we still want to display the original start-time
          startOfDay(slicedStart).valueOf() !== startOfDay(canonicalStart.marker).valueOf())
          ? slicedStart
          : canonicalStart.marker;
      const endDate = (!isEnd &&
          slicedEnd &&
          // See above HACK, but for end-time
          startOfDay(addMs(slicedEnd, -1)).valueOf() !== startOfDay(addMs(canonicalEnd.marker, -1)).valueOf())
          ? slicedEnd
          : canonicalEnd.marker;
      const startInstantMs = startDate === canonicalStart.marker ? canonicalStart.date.valueOf() : undefined;
      const endInstantMs = endDate === canonicalEnd.marker ? canonicalEnd.date.valueOf() : undefined;
      if (displayEventTime && !def.allDay) {
          if (displayEventEnd && (isStart || isEnd) && def.hasEnd) {
              // TODO: put this functionality in @full-ui/headless-calendar ?
              const rangeParts = dateEnv.formatRangeToParts(startDate, endDate, timeFormat, {
                  startInstantMs,
                  endInstantMs,
              });
              const multiDaySeparator = detectMultiDayTimes(rangeParts);
              // NOTE: produces strings like '12:00pm - 1:00pm', without condensing dayPeriod,
              // but that's okay since it's technically a different dayPeriod on a different day
              if (multiDaySeparator != null) {
                  return joinDateTimeFormatParts(dateEnv.formatToParts(startDate, timeFormat, {
                      instantMs: startInstantMs,
                  })) +
                      multiDaySeparator +
                      joinDateTimeFormatParts(dateEnv.formatToParts(endDate, timeFormat, {
                          instantMs: endInstantMs,
                      }));
              }
              return joinDateTimeFormatParts(rangeParts);
          }
          if (isStart) {
              return joinDateTimeFormatParts(dateEnv.formatToParts(startDate, timeFormat, {
                  instantMs: startInstantMs,
              }));
          }
      }
      return '';
  }
  const dateUnits = new Set(['year', 'month', 'day']); // TODO: DRY
  function detectMultiDayTimes(parts) {
      let sharedPart;
      let hasDatePart = false;
      for (const part of parts) {
          if (part.source === 'shared') {
              sharedPart = part;
          }
          if (dateUnits.has(part.type)) {
              hasDatePart = true;
          }
      }
      return hasDatePart ? sharedPart.value : undefined;
  }
  function getEventRangeMeta(eventRange, todayRange, nowDate, nowMs) {
      let segRange = eventRange.range;
      return {
          isPast: segRange.instantEndMs != null && nowMs != null
              ? segRange.instantEndMs <= nowMs
              : segRange.end <= (nowDate || todayRange.start),
          isFuture: segRange.instantStartMs != null && nowMs != null
              ? segRange.instantStartMs >= nowMs
              : segRange.start >= (nowDate || todayRange.end),
          isToday: todayRange && rangeContainsMarker(todayRange, segRange.start),
      };
  }
  function buildEventRangeKey(eventRange) {
      return eventRange.instance
          ? eventRange.instance.instanceId
          : `${eventRange.def.defId}:${eventRange.range.start.toISOString()}`;
      // inverse-background events don't have specific instances. TODO: better solution
  }
  function getEventTagAndAttrs(eventRange, context) {
      let { def, instance } = eventRange;
      let { url } = def;
      if (url) {
          return ['a', { href: url }, true];
      }
      let { emitter, options } = context;
      let { eventInteractive } = options;
      if (eventInteractive == null) {
          eventInteractive = def.interactive;
          if (eventInteractive == null) {
              eventInteractive = Boolean(emitter.hasHandlers('eventClick'));
          }
      }
      let attrs;
      // mock what happens in EventClicking
      if (eventInteractive) {
          // only attach keyboard-related handlers because click handler is already done in EventClicking
          attrs = createAriaKeyboardAttrs((ev) => {
              emitter.trigger('eventClick', {
                  el: ev.target,
                  event: new EventImpl(context, def, instance),
                  jsEvent: ev,
                  view: context.viewApi,
              });
          });
          attrs = { role: 'button', ...attrs };
      }
      return ['div', attrs, eventInteractive];
  }

  const classNamesRe = /(^c|C)lass(Name)?$/;
  const contentRe = /Content$/;
  const lifecycleRe = /(DidMount|WillUnmount)$/;
  const handlerRe = /^on[A-Z]/;
  // Somewhat tracks COMPLEX_OPTION_COMPARATORS
  // Unfortunately always need 'maybe' to handle undefined inital value, because of CalendarDataManager
  const customMergeFuncs = {
      buttons: mergeMaybePropsDepth1,
  };
  function mergeViewOptionsMap(...hashes) {
      const merged = {};
      for (const hash of hashes) {
          for (const viewName in hash) {
              const viewOptions = hash[viewName];
              if (!merged[viewName]) {
                  merged[viewName] = viewOptions;
              }
              else {
                  merged[viewName] = mergeCalendarOptions(merged[viewName], viewOptions);
              }
          }
      }
      return merged;
  }
  /*
  Merges an array of RAW options objects into a single object.
  The second argument allows for an array of property names who's object values will be merged together.
  */
  function mergeCalendarOptions(...optionSets) {
      let dest = {};
      for (const options of optionSets) {
          for (let name in options) {
              if (name in dest) {
                  const mergeFunc = customMergeFuncs[name] || (classNamesRe.test(name) ? joinFuncishClassNames :
                      contentRe.test(name) ? mergeContentInjectors :
                          lifecycleRe.test(name) ? mergeLifecycleCallbacks : undefined);
                  dest[name] = mergeFunc
                      ? mergeFunc(dest[name], options[name], name)
                      : options[name]; // last wins
              }
              else {
                  dest[name] = options[name]; // last wins
              }
          }
      }
      return dest;
  }
  /*
  Called while merging raw option objects, before the normal option refinement pass.
  ClassName values are validated here because merging may join raw strings, or build a
  combined function that joins raw generator outputs later. Without checking each part
  before joinClassNames, invalid values like objects/arrays could be stringified into
  valid-looking class strings before refineClassName/refineClassNameGenerator see them.

  Ideally this would be a single-pass responsibility: either merge after refinement, or
  store unjoined class parts during raw merging and have one later refiner validate and
  join all parts. For now, this merge helper validates just enough to avoid corrupting
  invalid values before the formal refinement pass.
  */
  function joinFuncishClassNames(input0, // added to string first
  input1, optionName) {
      const isFunc0 = typeof input0 === 'function';
      const isFunc1 = typeof input1 === 'function';
      if (isFunc0 || isFunc1) {
          const combinedFunc = (info) => {
              return joinClassNames(refineClassName(isFunc0 ? input0(info) : input0, optionName), refineClassName(isFunc1 ? input1(info) : input1, optionName));
          };
          combinedFunc.parts = [input0, input1]; // see CalendarDataManager::processRawCalendarOptions
          return combinedFunc;
      }
      return joinClassNames(refineClassName(input0, optionName), refineClassName(input1, optionName));
  }
  function mergeContentInjectors(contentGenerator0, // fallback
  contentGenerator1) {
      if (typeof contentGenerator1 === 'function') {
          // fabricate new function
          const combinedFunc = (renderProps) => {
              const res = contentGenerator1(renderProps);
              if (res === true) { // `true` indicates use-fallback
                  if (typeof contentGenerator0 === 'function') {
                      return contentGenerator0(renderProps);
                  }
                  return contentGenerator0;
              }
              return res;
          };
          combinedFunc.parts = [contentGenerator0, contentGenerator1]; // see CalendarDataManager::processRawCalendarOptions
          return combinedFunc;
      }
      if (contentGenerator1 != null) {
          return contentGenerator1;
      }
      return contentGenerator0;
  }
  function mergeLifecycleCallbacks(fn0, // called first
  fn1) {
      if (fn0 && fn1) {
          // fabricate new function
          const combinedFunc = (...args) => {
              fn0(...args);
              fn1(...args);
          };
          combinedFunc.parts = [fn0, fn1]; // see CalendarDataManager::processRawCalendarOptions
          return combinedFunc;
      }
      return fn0 || fn1;
  }
  function isNonHandlerPropsEqual(obj0, obj1) {
      const keys = getUnequalProps(obj0, obj1);
      for (let key of keys) {
          if (!handlerRe.test(key)) {
              return false;
          }
      }
      return true;
  }
  function isMergedPropsEqual(val0, val1) {
      const parts0 = val0 && val0.parts;
      const parts1 = val1 && val1.parts;
      if (parts0 && parts1) {
          const count0 = parts0.length;
          const count1 = parts1.length;
          if (count0 !== count1) {
              return false;
          }
          for (let i = 0; i < count0; i++) {
              if (!(parts0[i] === parts1[i] || isMergedPropsEqual(parts0[i], parts1[i]))) {
                  return false;
              }
          }
          return true;
      }
      return false;
  }

  const globalLocales = [];

  const MINIMAL_RAW_EN_LOCALE = {
      code: 'en',
      week: {
          dow: 0, // Sunday is the first day of the week
          doy: 4, // 4 days need to be within the year to be considered the first week
      },
      direction: 'ltr', // TODO: make a real type for this
      todayText: 'Today',
      prevText: 'Prev',
      nextText: 'Next',
      prevYearText: 'Prev year',
      nextYearText: 'Next year',
      yearText: 'Year',
      monthText: 'Month',
      weekTextLong: 'Week',
      dayText: 'Day',
      listText: 'List',
      closeHint: 'Close',
      eventsHint: 'Events',
      allDayText: 'All-day',
      timedText: 'Timed',
      moreLinkText: 'more',
      noEventsText: 'No events to display',
  };
  /*
  Includes things we don't want other locales to inherit,
  things that derive from other translatable strings.
  */
  const RAW_EN_LOCALE = {
      ...MINIMAL_RAW_EN_LOCALE,
      // if a locale doesn't define this, fall back to weekTextLong, don't use EN
      weekTextShort: 'W',
      todayHint: (unitText, unit) => {
          return (unit === 'day')
              ? 'Today'
              : `This ${unitText}`;
      },
      prevHint: 'Previous $0',
      nextHint: 'Next $0',
      viewHint: '$0 view',
      viewChangeHint: 'Change view',
      navLinkHint: 'Go to $0',
      moreLinkHint(eventCnt) {
          return `Show ${eventCnt} more event${eventCnt === 1 ? '' : 's'}`;
      },
  };
  function organizeRawLocales(explicitRawLocales) {
      let defaultCode = explicitRawLocales.length > 0 ? explicitRawLocales[0].code : 'en';
      let allRawLocales = globalLocales.concat(explicitRawLocales);
      let rawLocaleMap = {
          en: RAW_EN_LOCALE,
      };
      for (let rawLocale of allRawLocales) {
          rawLocaleMap[rawLocale.code] = rawLocale;
      }
      return {
          map: rawLocaleMap,
          defaultCode,
      };
  }
  function buildLocale(inputSingular, available) {
      if (typeof inputSingular === 'object' && !Array.isArray(inputSingular)) {
          return parseLocale(inputSingular.code, [inputSingular.code], inputSingular);
      }
      return queryLocale(inputSingular, available);
  }
  function queryLocale(codeArg, available) {
      let codes = [].concat(codeArg || []); // will convert to array
      let raw = queryRawLocale(codes, available) || RAW_EN_LOCALE;
      return parseLocale(codeArg, codes, raw);
  }
  function queryRawLocale(codes, available) {
      for (let i = 0; i < codes.length; i += 1) {
          let parts = codes[i].toLocaleLowerCase().split('-');
          for (let j = parts.length; j > 0; j -= 1) {
              let simpleId = parts.slice(0, j).join('-');
              if (available[simpleId]) {
                  return available[simpleId];
              }
          }
      }
      return null;
  }
  function parseLocale(codeArg, codes, raw) {
      let merged = mergeCalendarOptions(MINIMAL_RAW_EN_LOCALE, raw);
      delete merged.code; // don't want this part of the options
      let { week } = merged;
      delete merged.week;
      return {
          codeArg,
          codes,
          week,
          simpleNumberFormat: new Intl.NumberFormat(codeArg),
          options: merged,
      };
  }

  class JsonRequestError extends Error {
      constructor(message, response) {
          super(message);
          this.response = response;
      }
  }
  function requestJson(method, url, params) {
      method = method.toUpperCase();
      const fetchOptions = {
          method,
      };
      if (method === 'GET') {
          url += (url.indexOf('?') === -1 ? '?' : '&') +
              new URLSearchParams(params);
      }
      else {
          fetchOptions.body = new URLSearchParams(params);
          fetchOptions.headers = {
              'Content-Type': 'application/x-www-form-urlencoded',
          };
      }
      return fetch(url, fetchOptions).then((fetchRes) => {
          if (fetchRes.ok) {
              return fetchRes.json().then((parsedResponse) => {
                  return [parsedResponse, fetchRes];
              }, () => {
                  throw new JsonRequestError('Failure parsing JSON', fetchRes);
              });
          }
          else {
              throw new JsonRequestError('Request failed', fetchRes);
          }
      });
  }

  function handleDateProfile(dateProfile, context) {
      context.emitter.trigger('datesSet', {
          ...buildRangeApiWithTimeZone(dateProfile.activeRange, context.dateEnv),
          view: context.viewApi,
      });
  }

  function handleEventStore(eventStore, context) {
      let { emitter } = context;
      if (emitter.hasHandlers('eventsSet')) {
          emitter.trigger('eventsSet', buildEventApis(eventStore, context));
      }
  }

  let eventSourceDef$2 = {
      ignoreRange: true,
      parseMeta(refined) {
          if (Array.isArray(refined.events)) {
              return refined.events;
          }
          return null;
      },
      fetch(arg, successCallback) {
          successCallback({
              rawEvents: arg.eventSource.meta,
          });
      },
  };
  const arrayEventSourcePlugin = {
      name: 'array-event-source',
      eventSourceDefs: [eventSourceDef$2],
  };

  /*
  given a function that resolves a result asynchronously.
  the function can either call passed-in success and failure callbacks,
  or it can return a promise.
  if you need to pass additional params to func, bind them first.
  */
  function unpromisify(func, normalizedSuccessCallback, normalizedFailureCallback) {
      // guard against success/failure callbacks being called more than once
      // and guard against a promise AND callback being used together.
      let isResolved = false;
      let wrappedSuccess = function (res) {
          if (!isResolved) {
              isResolved = true;
              normalizedSuccessCallback(res);
          }
      };
      let wrappedFailure = function (error) {
          if (!isResolved) {
              isResolved = true;
              normalizedFailureCallback(error);
          }
      };
      let res = func(wrappedSuccess, wrappedFailure);
      if (res && typeof res.then === 'function') {
          res.then(wrappedSuccess, wrappedFailure);
      }
  }

  let eventSourceDef$1 = {
      parseMeta(refined) {
          if (typeof refined.events === 'function') {
              return refined.events;
          }
          return null;
      },
      fetch(arg, successCallback, errorCallback) {
          const { dateEnv } = arg.context;
          const func = arg.eventSource.meta;
          unpromisify(func.bind(null, buildRangeApiWithTimeZone(arg.range, dateEnv)), (rawEvents) => successCallback({ rawEvents }), errorCallback);
      },
  };
  const funcEventSourcePlugin = {
      name: 'func-event-source',
      eventSourceDefs: [eventSourceDef$1],
  };

  const JSON_FEED_EVENT_SOURCE_REFINERS = {
      method: String,
      extraParams: identity,
      startParam: String,
      endParam: String,
      timeZoneParam: String,
  };

  let eventSourceDef = {
      parseMeta(refined) {
          if (refined.url && (refined.format === 'json' || !refined.format)) {
              return {
                  url: refined.url,
                  format: 'json',
                  method: (refined.method || 'GET').toUpperCase(),
                  extraParams: refined.extraParams,
                  startParam: refined.startParam,
                  endParam: refined.endParam,
                  timeZoneParam: refined.timeZoneParam,
              };
          }
          return null;
      },
      fetch(arg, successCallback, errorCallback) {
          const { meta } = arg.eventSource;
          const requestParams = buildRequestParams(meta, arg.range, arg.context);
          requestJson(meta.method, meta.url, requestParams).then(([rawEvents, response]) => {
              successCallback({ rawEvents, response });
          }, errorCallback);
      },
  };
  const jsonFeedEventSourcePlugin = {
      name: 'json-event-source',
      eventSourceRefiners: JSON_FEED_EVENT_SOURCE_REFINERS,
      eventSourceDefs: [eventSourceDef],
  };
  function buildRequestParams(meta, range, context) {
      let { dateEnv, options } = context;
      let startParam;
      let endParam;
      let timeZoneParam;
      let customRequestParams;
      let params = {};
      startParam = meta.startParam;
      if (startParam == null) {
          startParam = options.startParam;
      }
      endParam = meta.endParam;
      if (endParam == null) {
          endParam = options.endParam;
      }
      timeZoneParam = meta.timeZoneParam;
      if (timeZoneParam == null) {
          timeZoneParam = options.timeZoneParam;
      }
      // retrieve any outbound GET/POST data from the options
      if (typeof meta.extraParams === 'function') {
          // supplied as a function that returns a key/value object
          customRequestParams = meta.extraParams();
      }
      else {
          // probably supplied as a straight key/value object
          customRequestParams = meta.extraParams || {};
      }
      Object.assign(params, customRequestParams);
      params[startParam] = dateEnv.formatIso(range.start);
      params[endParam] = dateEnv.formatIso(range.end);
      if (dateEnv.timeZone !== 'local') {
          params[timeZoneParam] = dateEnv.timeZone;
      }
      return params;
  }

  const changeHandlerPlugin = {
      name: 'change-handler',
      optionChangeHandlers: {
          controller(controller, context) {
              // TODO: the initial setting is in CalendarDataManager
              controller._setApi(context.calendarApi);
          },
          events(events, context) {
              handleEventSources([events], context);
          },
          eventSources: handleEventSources,
      },
  };
  /*
  BUG: if `event` was supplied, all previously-given `eventSources` will be wiped out
  */
  function handleEventSources(inputs, context) {
      let unfoundSources = hashValuesToArray(context.getCurrentData().eventSources);
      if (unfoundSources.length === 1 &&
          inputs.length === 1 &&
          Array.isArray(unfoundSources[0]._raw) &&
          Array.isArray(inputs[0])) {
          context.dispatch({
              type: 'RESET_RAW_EVENTS',
              sourceId: unfoundSources[0].sourceId,
              rawEvents: inputs[0],
          });
          return;
      }
      let newInputs = [];
      for (let input of inputs) {
          let inputFound = false;
          for (let i = 0; i < unfoundSources.length; i += 1) {
              if (unfoundSources[i]._raw === input) {
                  unfoundSources.splice(i, 1); // delete
                  inputFound = true;
                  break;
              }
          }
          if (!inputFound) {
              newInputs.push(input);
          }
      }
      for (let unfoundSource of unfoundSources) {
          context.dispatch({
              type: 'REMOVE_EVENT_SOURCE',
              sourceId: unfoundSource.sourceId,
          });
      }
      for (let newInput of newInputs) {
          context.calendarApi.addEventSource(newInput);
      }
  }

  const EVENT_SOURCE_REFINERS = {
      id: String,
      defaultAllDay: Boolean,
      url: String,
      format: String,
      events: identity, // array or function
      eventDataTransform: identity,
      // for any network-related sources
      success: identity,
      failure: identity,
  };
  function parseEventSource(raw, context, refiners = buildEventSourceRefiners(context)) {
      let rawObj;
      if (typeof raw === 'string') {
          rawObj = { url: raw };
      }
      else if (typeof raw === 'function' || Array.isArray(raw)) {
          rawObj = { events: raw };
      }
      else if (typeof raw === 'object' && raw) { // not null
          rawObj = raw;
      }
      if (rawObj) {
          let { refined, extra } = refineProps(rawObj, refiners);
          let metaRes = buildEventSourceMeta(refined, context);
          if (metaRes) {
              return {
                  _raw: raw,
                  isFetching: false,
                  latestFetchId: '',
                  fetchRange: null,
                  defaultAllDay: refined.defaultAllDay,
                  eventDataTransform: refined.eventDataTransform,
                  success: refined.success,
                  failure: refined.failure,
                  publicId: refined.id || '',
                  sourceId: guid(),
                  sourceDefId: metaRes.sourceDefId,
                  meta: metaRes.meta,
                  ui: createEventUi(refined, context),
                  extendedProps: extra,
              };
          }
      }
      return null;
  }
  function buildEventSourceRefiners(context) {
      return { ...EVENT_UI_REFINERS, ...EVENT_SOURCE_REFINERS, ...context.pluginHooks.eventSourceRefiners };
  }
  function buildEventSourceMeta(raw, context) {
      let defs = context.pluginHooks.eventSourceDefs;
      for (let i = defs.length - 1; i >= 0; i -= 1) { // later-added plugins take precedence
          let def = defs[i];
          let meta = def.parseMeta(raw);
          if (meta) {
              return { sourceDefId: i, meta };
          }
      }
      return null;
  }

  function initEventSources(calendarOptions, dateProfile, context) {
      let activeRange = dateProfile ? dateProfile.activeRange : null;
      return addSources({}, parseInitialSources(calendarOptions, context), activeRange, context);
  }
  function reduceEventSources(eventSources, action, dateProfile, context) {
      let activeRange = dateProfile ? dateProfile.activeRange : null; // need this check?
      switch (action.type) {
          case 'ADD_EVENT_SOURCES': // already parsed
              return addSources(eventSources, action.sources, activeRange, context);
          case 'REMOVE_EVENT_SOURCE':
              return removeSource(eventSources, action.sourceId);
          case 'PREV': // TODO: how do we track all actions that affect dateProfile :(
          case 'NEXT':
          case 'CHANGE_DATE':
          case 'CHANGE_VIEW_TYPE':
              if (dateProfile) {
                  return fetchDirtySources(eventSources, activeRange, context);
              }
              return eventSources;
          case 'FETCH_EVENT_SOURCES':
              return fetchSourcesByIds(eventSources, action.sourceIds ? // why no type?
                  arrayToHash(action.sourceIds) :
                  excludeStaticSources(eventSources, context), activeRange, action.isRefetch || false, context);
          case 'RECEIVE_EVENTS':
          case 'RECEIVE_EVENT_ERROR':
              return receiveResponse(eventSources, action.sourceId, action.fetchId, action.fetchRange);
          case 'REMOVE_ALL_EVENT_SOURCES':
              return {};
          default:
              return eventSources;
      }
  }
  function reduceEventSourcesNewTimeZone(eventSources, dateProfile, context) {
      let activeRange = dateProfile ? dateProfile.activeRange : null; // need this check?
      return fetchSourcesByIds(eventSources, excludeStaticSources(eventSources, context), activeRange, true, context);
  }
  function computeEventSourcesLoading(eventSources) {
      for (let sourceId in eventSources) {
          if (eventSources[sourceId].isFetching) {
              return true;
          }
      }
      return false;
  }
  function addSources(eventSourceHash, sources, fetchRange, context) {
      let hash = {};
      for (let source of sources) {
          hash[source.sourceId] = source;
      }
      if (fetchRange) {
          hash = fetchDirtySources(hash, fetchRange, context);
      }
      return { ...eventSourceHash, ...hash };
  }
  function removeSource(eventSourceHash, sourceId) {
      return filterHash(eventSourceHash, (eventSource) => eventSource.sourceId !== sourceId);
  }
  function fetchDirtySources(sourceHash, fetchRange, context) {
      return fetchSourcesByIds(sourceHash, filterHash(sourceHash, (eventSource) => isSourceDirty(eventSource, fetchRange, context)), fetchRange, false, context);
  }
  function isSourceDirty(eventSource, fetchRange, context) {
      if (!doesSourceNeedRange(eventSource, context)) {
          return !eventSource.latestFetchId;
      }
      return !context.options.lazyFetching ||
          !eventSource.fetchRange ||
          eventSource.isFetching || // always cancel outdated in-progress fetches
          fetchRange.start < eventSource.fetchRange.start ||
          fetchRange.end > eventSource.fetchRange.end;
  }
  function fetchSourcesByIds(prevSources, sourceIdHash, fetchRange, isRefetch, context) {
      let nextSources = {};
      for (let sourceId in prevSources) {
          let source = prevSources[sourceId];
          if (sourceIdHash[sourceId]) {
              nextSources[sourceId] = fetchSource(source, fetchRange, isRefetch, context);
          }
          else {
              nextSources[sourceId] = source;
          }
      }
      return nextSources;
  }
  function fetchSource(eventSource, fetchRange, isRefetch, context) {
      let { options, calendarApi } = context;
      let sourceDef = context.pluginHooks.eventSourceDefs[eventSource.sourceDefId];
      let fetchId = guid();
      sourceDef.fetch({
          eventSource,
          range: fetchRange,
          isRefetch,
          context,
      }, (res) => {
          let { rawEvents } = res;
          if (options.eventSourceSuccess) {
              rawEvents = options.eventSourceSuccess.call(calendarApi, rawEvents, res.response) || rawEvents;
          }
          if (eventSource.success) {
              rawEvents = eventSource.success.call(calendarApi, rawEvents, res.response) || rawEvents;
          }
          context.dispatch({
              type: 'RECEIVE_EVENTS',
              sourceId: eventSource.sourceId,
              fetchId,
              fetchRange,
              rawEvents,
          });
      }, (error) => {
          let errorHandled = false;
          if (options.eventSourceFailure) {
              options.eventSourceFailure.call(calendarApi, error);
              errorHandled = true;
          }
          if (eventSource.failure) {
              eventSource.failure(error);
              errorHandled = true;
          }
          if (!errorHandled) {
              warn(`Unhandled event source error: ${error.message}`, error);
          }
          context.dispatch({
              type: 'RECEIVE_EVENT_ERROR',
              sourceId: eventSource.sourceId,
              fetchId,
              fetchRange,
              error,
          });
      });
      return {
          ...eventSource,
          isFetching: true,
          latestFetchId: fetchId,
      };
  }
  function receiveResponse(sourceHash, sourceId, fetchId, fetchRange) {
      let eventSource = sourceHash[sourceId];
      if (eventSource && // not already removed
          fetchId === eventSource.latestFetchId) {
          return {
              ...sourceHash,
              [sourceId]: {
                  ...eventSource,
                  isFetching: false,
                  fetchRange, // also serves as a marker that at least one fetch has completed
              },
          };
      }
      return sourceHash;
  }
  function excludeStaticSources(eventSources, context) {
      return filterHash(eventSources, (eventSource) => doesSourceNeedRange(eventSource, context));
  }
  function parseInitialSources(rawOptions, context) {
      let refiners = buildEventSourceRefiners(context);
      let rawSources = [].concat(rawOptions.eventSources || []);
      let sources = []; // parsed
      if (rawOptions.initialEvents) {
          rawSources.unshift(rawOptions.initialEvents);
      }
      if (rawOptions.events) {
          rawSources.unshift(rawOptions.events);
      }
      for (let rawSource of rawSources) {
          let source = parseEventSource(rawSource, context, refiners);
          if (source) {
              sources.push(source);
          }
      }
      return sources;
  }
  function doesSourceNeedRange(eventSource, context) {
      let defs = context.pluginHooks.eventSourceDefs;
      return !defs[eventSource.sourceDefId].ignoreRange;
  }

  const SIMPLE_RECURRING_REFINERS = {
      daysOfWeek: identity,
      startTime: createDuration,
      endTime: createDuration,
      duration: createDuration,
      startRecur: identity,
      endRecur: identity,
  };

  let recurring = {
      parse(refined, dateEnv) {
          if (refined.daysOfWeek || refined.startTime || refined.endTime || refined.startRecur || refined.endRecur) {
              let recurringData = {
                  daysOfWeek: refined.daysOfWeek || null,
                  startTime: refined.startTime || null,
                  endTime: refined.endTime || null,
                  startRecur: refined.startRecur ? dateEnv.createMarker(refined.startRecur) : null,
                  endRecur: refined.endRecur ? dateEnv.createMarker(refined.endRecur) : null,
                  dateEnv,
              };
              let duration;
              if (refined.duration) {
                  duration = refined.duration;
              }
              if (!duration && refined.startTime && refined.endTime) {
                  duration = subtractDurations(refined.endTime, refined.startTime);
              }
              return {
                  allDayGuess: Boolean(!refined.startTime && !refined.endTime),
                  duration,
                  typeData: recurringData, // doesn't need endTime anymore but oh well
              };
          }
          return null;
      },
      expand(typeData, framingRange, dateEnv) {
          let clippedFramingRange = intersectRanges(framingRange, { start: typeData.startRecur, end: typeData.endRecur });
          if (clippedFramingRange) {
              return expandRanges(typeData.daysOfWeek, typeData.startTime, typeData.dateEnv, dateEnv, clippedFramingRange);
          }
          return [];
      },
  };
  const simpleRecurringEventsPlugin = {
      name: 'simple-recurring-event',
      recurringTypes: [recurring],
      eventRefiners: SIMPLE_RECURRING_REFINERS,
  };
  function expandRanges(daysOfWeek, startTime, eventDateEnv, calendarDateEnv, framingRange) {
      let dowHash = daysOfWeek ? arrayToHash(daysOfWeek) : null;
      let dayMarker = startOfDay(framingRange.start);
      let endMarker = framingRange.end;
      let instanceStarts = [];
      // https://github.com/fullcalendar/fullcalendar/issues/7934
      if (startTime) {
          if (startTime.milliseconds < 0) {
              // possible for next-day to have negative business hours that go into current day
              endMarker = addDays(endMarker, 1);
          }
          else if (startTime.milliseconds >= 1000 * 60 * 60 * 24) {
              // possible for prev-day to have >24hr business hours that go into current day
              dayMarker = addDays(dayMarker, -1);
          }
      }
      while (dayMarker < endMarker) {
          let instanceStart;
          // if everyday, or this particular day-of-week
          if (!dowHash || dowHash[dayMarker.getUTCDay()]) {
              if (startTime) {
                  instanceStart = calendarDateEnv.add(dayMarker, startTime);
              }
              else {
                  instanceStart = dayMarker;
              }
              instanceStarts.push(calendarDateEnv.createMarker(eventDateEnv.toDate(instanceStart)));
          }
          dayMarker = addDays(dayMarker, 1);
      }
      return instanceStarts;
  }

  /*
  this array is exposed on the root namespace so that UMD plugins can add to it.
  see the rollup-bundles script.
  */
  const globalPlugins = [
      arrayEventSourcePlugin,
      funcEventSourcePlugin,
      jsonFeedEventSourcePlugin,
      simpleRecurringEventsPlugin,
      changeHandlerPlugin,
      {
          name: 'misc',
          isLoadingFuncs: [
              (state) => computeEventSourcesLoading(state.eventSources),
          ],
          propSetHandlers: {
              dateProfile: handleDateProfile,
              eventStore: handleEventStore,
          },
      },
  ];

  var r,u,i,f=[],c=l$2,e=c.__b,a=c.__r,v=c.diffed,l=c.__c,m=c.unmount,p=c.__;function j$1(){for(var n;n=f.shift();){var t=n.__H;if(n.__P&&t)try{t.__h.some(z),t.__h.some(B$1),t.__h=[];}catch(r){t.__h=[],c.__e(r,n.__v);}}}c.__b=function(n){r=null,e&&e(n);},c.__=function(n,t){n&&t.__k&&t.__k.__m&&(n.__m=t.__k.__m),p&&p(n,t);},c.__r=function(n){a&&a(n);var i=(r=n.__c).__H;i&&(u===r?(i.__h=[],r.__h=[],i.__.some(function(n){n.__N&&(n.__=n.__N),n.u=n.__N=void 0;})):(i.__h.some(z),i.__h.some(B$1),i.__h=[],0)),u=r;},c.diffed=function(n){v&&v(n);var t=n.__c;t&&t.__H&&(t.__H.__h.length&&(1!==f.push(t)&&i===c.requestAnimationFrame||((i=c.requestAnimationFrame)||w)(j$1)),t.__H.__.some(function(n){n.u&&(n.__H=n.u,n.u=void 0);})),u=r=null;},c.__c=function(n,t){t.some(function(n){try{n.__h.some(z),n.__h=n.__h.filter(function(n){return !n.__||B$1(n)});}catch(r){t.some(function(n){n.__h&&(n.__h=[]);}),t=[],c.__e(r,n.__v);}}),l&&l(n,t);},c.unmount=function(n){m&&m(n);var t,r=n.__c;r&&r.__H&&(r.__H.__.some(function(n){try{z(n);}catch(n){t=n;}}),r.__H=void 0,t&&c.__e(t,r.__v));};var k="function"==typeof requestAnimationFrame;function w(n){var t,r=function(){clearTimeout(u),k&&cancelAnimationFrame(t),setTimeout(n);},u=setTimeout(r,35);k&&(t=requestAnimationFrame(r));}function z(n){var t=r,u=n.__c;"function"==typeof u&&(n.__c=void 0,u()),r=t;}function B$1(n){var t=r;n.__c=n.__(),r=t;}

  function g(n,t){for(var e in t)n[e]=t[e];return n}function E(n,t){for(var e in n)if("__source"!==e&&!(e in t))return !0;for(var r in t)if("__source"!==r&&n[r]!==t[r])return !0;return !1}function M(n,t){this.props=n,this.context=t;}(M.prototype=new C).isPureReactComponent=!0,M.prototype.shouldComponentUpdate=function(n,t){return E(this.props,n)||E(this.state,t)};var T=l$2.__b;l$2.__b=function(n){n.type&&n.type.__f&&n.ref&&(n.props.ref=n.ref,n.ref=null),T&&T(n);};var O=l$2.__e;l$2.__e=function(n,t,e,r){if(n.then)for(var u,o=t;o=o.__;)if((u=o.__c)&&u.__c)return null==t.__e&&(t.__e=e.__e,t.__k=e.__k||[]),u.__c(n,t);O(n,t,e,r);};var U=l$2.unmount;function V(n,t,e){return n&&(n.__c&&n.__c.__H&&(n.__c.__H.__.forEach(function(n){"function"==typeof n.__c&&n.__c();}),n.__c.__H=null),null!=(n=g({},n)).__c&&(n.__c.__P===e&&(n.__c.__P=t),n.__c.__e=!0,n.__c=null),n.__k=n.__k&&n.__k.map(function(n){return V(n,t,e)})),n}function W(n,t,e){return n&&e&&(n.__v=null,n.__k=n.__k&&n.__k.map(function(n){return W(n,t,e)}),n.__c&&n.__c.__P===t&&(n.__e&&e.appendChild(n.__e),n.__c.__e=!0,n.__c.__P=e)),n}function P(){this.__u=0,this.o=null,this.__b=null;}function j(n){var t=n.__&&n.__.__c;return t&&t.__a&&t.__a(n)}function B(){this.i=null,this.l=null;}l$2.unmount=function(n){var t=n.__c;t&&(t.__z=!0),t&&t.__R&&t.__R(),t&&32&n.__u&&(n.type=null),U&&U(n);},(P.prototype=new C).__c=function(n,t){var e=t.__c,r=this;null==r.o&&(r.o=[]),r.o.push(e);var u=j(r.__v),o=!1,i=function(){o||r.__z||(o=!0,e.__R=null,u?u(f):f());};e.__R=i;var l=e.__P;e.__P=null;var f=function(){if(!--r.__u){if(r.state.__a){var n=r.state.__a;r.__v.__k[0]=W(n,n.__c.__P,n.__c.__O);}var t;for(r.setState({__a:r.__b=null});t=r.o.pop();)t.__P=l,t.forceUpdate();}};r.__u++||32&t.__u||r.setState({__a:r.__b=r.__v.__k[0]}),n.then(i,i);},P.prototype.componentWillUnmount=function(){this.o=[];},P.prototype.render=function(n,e){if(this.__b){if(this.__v.__k){var r=document.createElement("div"),o=this.__v.__k[0].__c;this.__v.__k[0]=V(this.__b,r,o.__O=o.__P);}this.__b=null;}var i=e.__a&&k$1(S,null,n.fallback);return i&&(i.__u&=-33),[k$1(S,null,e.__a?null:n.children),i]};var H=function(n,t,e){if(++e[1]===e[0]&&n.l.delete(t),n.props.revealOrder&&("t"!==n.props.revealOrder[0]||!n.l.size))for(e=n.i;e;){for(;e.length>3;)e.pop()();if(e[1]<e[0])break;n.i=e=e[2];}};function Z(n){return this.getChildContext=function(){return n.context},n.children}function Y(n){var e=this,r=n.h;if(e.componentWillUnmount=function(){R(null,e.v),e.v=null,e.h=null;},e.h&&e.h!==r&&e.componentWillUnmount(),!e.v){for(var u=e.__v;null!==u&&!u.__m&&null!==u.__;)u=u.__;e.h=r,e.v={nodeType:1,parentNode:r,childNodes:[],__k:{__m:u.__m},contains:function(){return !0},namespaceURI:r.namespaceURI,insertBefore:function(n,t){this.childNodes.push(n),e.h.insertBefore(n,t);},removeChild:function(n){this.childNodes.splice(this.childNodes.indexOf(n)>>>1,1),e.h.removeChild(n);}};}R(k$1(Z,{context:e.context},n.__v),e.v);}function $(n,e){var r=k$1(Y,{__v:n,h:e});return r.containerInfo=e,r}(B.prototype=new C).__a=function(n){var t=this,e=j(t.__v),r=t.l.get(n);return r[0]++,function(u){var o=function(){t.props.revealOrder?(r.push(u),H(t,n,r)):u();};e?e(o):o();}},B.prototype.render=function(n){this.i=null,this.l=new Map;var t=F(n.children);n.revealOrder&&"b"===n.revealOrder[0]&&t.reverse();for(var e=t.length;e--;)this.l.set(t[e],this.i=[1,0,this.i]);return n.children},B.prototype.componentDidUpdate=B.prototype.componentDidMount=function(){var n=this;this.l.forEach(function(t,e){H(n,e,t);});};var q="undefined"!=typeof Symbol&&Symbol.for&&Symbol.for("react.element")||60103,G=/^(?:accent|alignment|arabic|baseline|cap|clip(?!PathU)|color|dominant|fill|flood|font|glyph(?!R)|horiz|image(!S)|letter|lighting|marker(?!H|W|U)|overline|paint|pointer|shape|stop|strikethrough|stroke|text(?!L)|transform|underline|unicode|units|v|vector|vert|word|writing|x(?!C))[A-Z]/,J=/^on(Ani|Tra|Tou|BeforeInp|Compo)/,K=/[A-Z0-9]/g,Q="undefined"!=typeof document,X=function(n){return ("undefined"!=typeof Symbol&&"symbol"==typeof Symbol()?/fil|che|rad/:/fil|che|ra/).test(n)};function nn(n,t,e){return null==t.__k&&(t.textContent=""),R(n,t),"function"==typeof e&&e(),n?n.__c:null}C.prototype.isReactComponent=!0,["componentWillMount","componentWillReceiveProps","componentWillUpdate"].forEach(function(t){Object.defineProperty(C.prototype,t,{configurable:!0,get:function(){return this["UNSAFE_"+t]},set:function(n){Object.defineProperty(this,t,{configurable:!0,writable:!0,value:n});}});});var en=l$2.event;l$2.event=function(n){return en&&(n=en(n)),n.persist=function(){},n.isPropagationStopped=function(){return this.cancelBubble},n.isDefaultPrevented=function(){return this.defaultPrevented},n.nativeEvent=n};var un={configurable:!0,get:function(){return this.class}},on=l$2.vnode;l$2.vnode=function(n){"string"==typeof n.type&&function(n){var t=n.props,e=n.type,u={},o=-1==e.indexOf("-");for(var i in t){var l=t[i];if(!("value"===i&&"defaultValue"in t&&null==l||Q&&"children"===i&&"noscript"===e||"class"===i||"className"===i)){var f=i.toLowerCase();"defaultValue"===i&&"value"in t&&null==t.value?i="value":"download"===i&&!0===l?l="":"translate"===f&&"no"===l?l=!1:"o"===f[0]&&"n"===f[1]?"ondoubleclick"===f?i="ondblclick":"onchange"!==f||"input"!==e&&"textarea"!==e||X(t.type)?"onfocus"===f?i="onfocusin":"onblur"===f?i="onfocusout":J.test(i)&&(i=f):f=i="oninput":o&&G.test(i)?i=i.replace(K,"-$&").toLowerCase():null===l&&(l=void 0),"oninput"===f&&u[i=f]&&(i="oninputCapture"),u[i]=l;}}"select"==e&&(u.multiple&&Array.isArray(u.value)&&(u.value=F(t.children).forEach(function(n){n.props.selected=-1!=u.value.indexOf(n.props.value);})),null!=u.defaultValue&&(u.value=F(t.children).forEach(function(n){n.props.selected=u.multiple?-1!=u.defaultValue.indexOf(n.props.value):u.defaultValue==n.props.value;}))),t.class&&!t.className?(u.class=t.class,Object.defineProperty(u,"className",un)):t.className&&(u.class=u.className=t.className),n.props=u;}(n),n.$$typeof=q,on&&on(n);};var ln=l$2.__r;l$2.__r=function(n){ln&&ln(n),n.__c;};var fn=l$2.diffed;l$2.diffed=function(n){fn&&fn(n);var t=n.props,e=n.__e;null!=e&&"textarea"===n.type&&"value"in t&&t.value!==e.value&&(e.value=null==t.value?"":t.value);};function hn(n){return !!n&&n.$$typeof===q}function pn(n){return !!n.__k&&(R(null,n),!0)}var bn=function(n,t){var r,u=l$2.debounceRendering;l$2.debounceRendering=function(n){r=n;};try{var o=n(t);return r&&r(),o}finally{l$2.debounceRendering=u;}};

  function memoize(workerFunc, resEquality, teardownFunc) {
      let currentArgs;
      let currentRes;
      return function (...newArgs) {
          if (!currentArgs) {
              currentRes = workerFunc.apply(this, newArgs);
          }
          else if (!isArraysEqual(currentArgs, newArgs)) {
              if (teardownFunc) {
                  teardownFunc(currentRes);
              }
              let res = workerFunc.apply(this, newArgs);
              if (!resEquality || !resEquality(res, currentRes)) {
                  currentRes = res;
              }
          }
          currentArgs = newArgs;
          return currentRes;
      };
  }
  function memoizeObjArg(workerFunc, resEquality, teardownFunc) {
      let currentArg;
      let currentRes;
      return (newArg) => {
          if (!currentArg) {
              currentRes = workerFunc.call(this, newArg);
          }
          else if (!isPropsEqualShallow(currentArg, newArg)) {
              if (teardownFunc) {
                  teardownFunc(currentRes);
              }
              let res = workerFunc.call(this, newArg);
              if (!resEquality || !resEquality(res, currentRes)) {
                  currentRes = res;
              }
          }
          currentArg = newArg;
          return currentRes;
      };
  }

  const ViewContextType = X$1({}); // for Components
  function buildViewContext(viewSpec, viewApi, viewOptions, dateProfileGenerator, dateEnv, nowManager, pluginHooks, dispatch, getCurrentData, emitter, calendarApi, baseId, registerInteractiveComponent, unregisterInteractiveComponent) {
      return {
          dateEnv,
          nowManager,
          options: viewOptions,
          pluginHooks,
          emitter,
          dispatch,
          getCurrentData,
          calendarApi,
          viewSpec,
          viewApi,
          dateProfileGenerator,
          baseId,
          registerInteractiveComponent,
          unregisterInteractiveComponent,
      };
  }

  /* eslint max-classes-per-file: off */
  class PureComponent extends C {
      // debug: boolean
      shouldComponentUpdate(nextProps, nextState) {
          return !isPropsEqualWithMap(this.props, nextProps, this.propEquality /*, this.debug && 'props' */) ||
              !isPropsEqualWithMap(this.state, nextState, this.stateEquality /*, this.debug && 'state' */);
      }
  }
  PureComponent.addPropsEquality = addPropsEquality;
  PureComponent.addStateEquality = addStateEquality;
  PureComponent.contextType = ViewContextType;
  PureComponent.prototype.propEquality = {};
  PureComponent.prototype.stateEquality = {};
  class BaseComponent extends PureComponent {
  }
  BaseComponent.contextType = ViewContextType;
  function addPropsEquality(propEquality) {
      let hash = Object.create(this.prototype.propEquality);
      Object.assign(hash, propEquality);
      this.prototype.propEquality = hash;
  }
  function addStateEquality(stateEquality) {
      let hash = Object.create(this.prototype.stateEquality);
      Object.assign(hash, stateEquality);
      this.prototype.stateEquality = hash;
  }
  // use other one
  function setRef(ref, current) {
      if (typeof ref === 'function') {
          ref(current);
      }
      else if (ref) {
          // see https://github.com/facebook/react/issues/13029
          ref.current = current;
      }
  }

  class ContentInjector extends BaseComponent {
      constructor() {
          super(...arguments);
          this.id = guid();
          this.queuedDomNodes = [];
          this.currentDomNodes = [];
          this.handleEl = (el) => {
              this.el = el;
              if (this.props.elRef) {
                  setRef(this.props.elRef, el);
              }
          };
      }
      render() {
          const { props, context } = this;
          const { options } = context;
          const { customGenerator, defaultGenerator, renderProps } = props;
          const attrs = buildElAttrs(props, '', this.handleEl);
          let useDefault = false;
          let innerContent;
          let queuedDomNodes = [];
          let currentGeneratorMeta;
          if (customGenerator != null) {
              const customGeneratorRes = typeof customGenerator === 'function' ?
                  customGenerator(renderProps) :
                  customGenerator;
              if (customGeneratorRes === true) {
                  useDefault = true;
                  // NOTE: see how mergeContentInjectors also uses `true` to signal useDefault
              }
              else {
                  const isObject = customGeneratorRes && typeof customGeneratorRes === 'object'; // non-null
                  if (isObject && ('html' in customGeneratorRes)) {
                      attrs.dangerouslySetInnerHTML = { __html: customGeneratorRes.html };
                  }
                  else if (isObject && ('domNodes' in customGeneratorRes)) {
                      queuedDomNodes = Array.prototype.slice.call(customGeneratorRes.domNodes);
                  }
                  else if (isObject
                      ? hn(customGeneratorRes) // vdom node
                      : typeof customGeneratorRes !== 'function' // primitive value (like string or number)
                  ) {
                      // use in vdom
                      innerContent = customGeneratorRes;
                  }
                  else {
                      // an exotic object for handleCustomRendering
                      currentGeneratorMeta = customGeneratorRes;
                  }
              }
          }
          else {
              useDefault = !hasCustomRenderingHandler(props.generatorName, options);
          }
          if (useDefault && defaultGenerator) {
              innerContent = defaultGenerator(renderProps);
          }
          this.queuedDomNodes = queuedDomNodes;
          this.currentGeneratorMeta = currentGeneratorMeta;
          return k$1(props.tag, attrs, innerContent);
      }
      componentDidMount() {
          this.applyQueueudDomNodes();
          this.triggerCustomRendering(true);
      }
      componentDidUpdate() {
          this.applyQueueudDomNodes();
          this.triggerCustomRendering(true);
      }
      componentWillUnmount() {
          this.triggerCustomRendering(false); // TODO: different API for removal?
      }
      triggerCustomRendering(isActive) {
          const { props, context } = this;
          const { handleCustomRendering, customRenderingMetaMap } = context.options;
          if (handleCustomRendering) {
              const generatorMeta = this.currentGeneratorMeta ??
                  customRenderingMetaMap?.[props.generatorName];
              if (generatorMeta) {
                  handleCustomRendering({
                      id: this.id,
                      isActive,
                      containerEl: this.el,
                      generatorMeta,
                      renderProps: props.renderProps,
                  });
              }
          }
      }
      applyQueueudDomNodes() {
          const { queuedDomNodes, currentDomNodes } = this;
          const { el } = this;
          if (!isArraysEqual(queuedDomNodes, currentDomNodes)) {
              for (const domNode of currentDomNodes) {
                  domNode.remove();
              }
              for (let newNode of queuedDomNodes) {
                  el.appendChild(newNode);
              }
              this.currentDomNodes = queuedDomNodes;
          }
      }
  }
  ContentInjector.addPropsEquality({
      renderProps: isPropsEqualShallow,
      attrs: isNonHandlerPropsEqual,
      style: isPropsEqualShallow,
  });
  // Util
  /*
  Does UI-framework provide custom way of rendering that does not use Preact VDOM
  AND does the calendar's options define custom rendering?
  AKA. Should we NOT render the default content?
  */
  function hasCustomRenderingHandler(generatorName, options) {
      return Boolean(options.handleCustomRendering &&
          generatorName &&
          options.customRenderingMetaMap?.[generatorName]);
  }
  function buildElAttrs(props, className, elRef) {
      const attrs = { ...props.attrs, ref: elRef };
      if (props.className || className) {
          attrs.className = joinClassNames(className, props.className, attrs.className);
      }
      if (props.style) {
          attrs.style = props.style;
      }
      return attrs;
  }

  const RenderId = X$1(0);

  class ContentContainer extends C {
      constructor() {
          super(...arguments);
          this.InnerContent = InnerContentInjector.bind(undefined, this);
          this.handleEl = (el) => {
              this.el = el;
              if (this.props.elRef) {
                  setRef(this.props.elRef, el);
                  if (el && this.didMountMisfire) {
                      this.componentDidMount();
                  }
              }
          };
      }
      render() {
          const { props } = this;
          const generatedClassName = generateClassName(props.classNameGenerator, props.renderProps);
          if (props.children) {
              const attrs = buildElAttrs(props, generatedClassName, this.handleEl);
              const children = props.children(this.InnerContent, props.renderProps, attrs);
              if (props.tag) {
                  return k$1(props.tag, attrs, children);
              }
              else {
                  return children;
              }
          }
          else {
              return k$1((ContentInjector), {
                  ...props,
                  elRef: this.handleEl,
                  tag: props.tag || 'div',
                  className: joinClassNames(props.className, generatedClassName),
                  renderId: this.context,
              });
          }
      }
      componentDidMount() {
          if (this.el) {
              this.props.didMount?.({
                  ...this.props.renderProps,
                  el: this.el,
              });
          }
          else {
              this.didMountMisfire = true;
          }
      }
      componentWillUnmount() {
          this.props.willUnmount?.({
              ...this.props.renderProps,
              el: this.el,
          });
      }
  }
  ContentContainer.contextType = RenderId;
  function InnerContentInjector(containerComponent, props) {
      const parentProps = containerComponent.props;
      return k$1((ContentInjector), {
          renderProps: parentProps.renderProps,
          generatorName: parentProps.generatorName,
          customGenerator: parentProps.customGenerator,
          defaultGenerator: parentProps.defaultGenerator,
          renderId: containerComponent.context,
          ...props,
      });
  }
  // Utils
  function generateClassName(classNameGenerator, renderProps) {
      return (typeof classNameGenerator === 'function' ?
          classNameGenerator(renderProps) :
          classNameGenerator) || ''; // handles undefined
  }
  function renderText$1(renderProps) {
      return renderProps.text;
  }

  function getIsHeightAuto(options) {
      return options.height === 'auto' || options.contentHeight === 'auto';
  }
  function getTableHeaderSticky(options) {
      let { tableHeaderSticky } = options;
      if (tableHeaderSticky == null || tableHeaderSticky === 'auto') {
          tableHeaderSticky = getIsHeightAuto(options);
      }
      return tableHeaderSticky;
  }
  function getFooterScrollbarSticky(options) {
      const isHeightAuto = getIsHeightAuto(options);
      let { footerScrollbarSticky } = options;
      if (footerScrollbarSticky == null || footerScrollbarSticky === 'auto') {
          footerScrollbarSticky = isHeightAuto;
      }
      return Boolean(footerScrollbarSticky) && isHeightAuto;
  }
  function getScrollerSyncerClass(pluginHooks) {
      const ScrollerSyncer = pluginHooks.scrollerSyncerClass;
      if (!ScrollerSyncer) {
          throw new RangeError('Must import @fullcalendar/scrollgrid');
      }
      return ScrollerSyncer;
  }

  class NowTimerRunner {
      constructor(handleChange) {
          this.handleChange = handleChange;
          this.isMounted = false;
          this.handleRefresh = () => {
              let timing = this.computeTiming();
              if (timing.nowDate.valueOf() !== this.nowDate.valueOf() ||
                  timing.nowMs !== this.nowMs // marker alone can't detect fold-hour changes
              ) {
                  this.nowDate = timing.nowDate;
                  this.nowMs = timing.nowMs;
                  this.todayRange = timing.todayRange;
                  this.handleChange();
              }
              this.clearTimeout();
              this.setTimeout(timing.waitMs);
          };
          this.handleVisibilityChange = () => {
              if (!document.hidden) {
                  this.handleRefresh();
              }
          };
      }
      update(input) {
          if (!this.isMounted) {
              this.isMounted = true;
              // init inputs
              this.unit = input.unit;
              this.unitValue = input.unitValue;
              this.nowIndicatorSnap = input.nowIndicatorSnap;
              this.nowManager = input.nowManager;
              this.dateEnv = input.dateEnv;
              // init outputs
              const timing = this.computeTiming();
              this.nowDate = timing.nowDate;
              this.nowMs = timing.nowMs;
              this.todayRange = timing.todayRange;
              // init listeners
              this.setTimeout(timing.waitMs);
              this.nowManager.addResetListener(this.handleRefresh);
              // fired tab becomes visible after being hidden
              // SSR check. CalendarDataManager calls top-level sync :(
              if (typeof document !== 'undefined') {
                  document.addEventListener('visibilitychange', this.handleVisibilityChange);
              }
          }
          else if (input.unit !== this.unit ||
              input.unitValue !== this.unitValue ||
              input.nowIndicatorSnap !== this.nowIndicatorSnap ||
              input.nowManager !== this.nowManager ||
              input.dateEnv !== this.dateEnv) {
              // update inputs
              this.unit = input.unit;
              this.unitValue = input.unitValue;
              this.nowIndicatorSnap = input.nowIndicatorSnap;
              this.nowManager = input.nowManager;
              this.dateEnv = input.dateEnv;
              // recompute outputs — a dateEnv (timezone) change re-projects the same exact "now"
              // to a different civil time. (the nowManager reset listener can't do this: it fires
              // before this runner receives the new dateEnv, so it recomputes with the old one)
              const timing = this.computeTiming();
              this.nowDate = timing.nowDate;
              this.nowMs = timing.nowMs;
              this.todayRange = timing.todayRange;
              this.clearTimeout();
              this.setTimeout(timing.waitMs);
          }
          return {
              nowDate: this.nowDate,
              nowMs: this.nowMs,
              todayRange: this.todayRange,
          };
      }
      destroy() {
          if (this.isMounted) {
              this.isMounted = false;
              this.clearTimeout();
              this.nowManager.removeResetListener(this.handleRefresh);
              // SSR check. CalendarDataManager calls top-level sync :(
              if (typeof document !== 'undefined') {
                  document.removeEventListener('visibilitychange', this.handleVisibilityChange);
              }
          }
      }
      computeTiming() {
          let { unit, unitValue, nowIndicatorSnap, dateEnv } = this;
          let unroundedNowMs = this.nowManager.getEpochMs();
          let unroundedNow = dateEnv.timestampToMarker(unroundedNowMs);
          if (nowIndicatorSnap === 'auto') {
              nowIndicatorSnap =
                  // large unit?
                  /year|month|week|day/.test(unit) ||
                      // if slotDuration 30 mins for example, would NOT appear to snap (legacy behavior)
                      (unitValue || 1) === 1;
          }
          let nowDate;
          let nowMs;
          let waitMs;
          if (nowIndicatorSnap) {
              nowDate = dateEnv.startOf(unroundedNow, unit); // aka currentUnitStart
              nowMs = resolveSnappedInstant(nowDate, unroundedNowMs, dateEnv);
              let nextUnitStart = dateEnv.add(nowDate, createDuration(1, unit));
              waitMs = resolveNextSnappedInstant(nextUnitStart, unroundedNowMs, dateEnv) - unroundedNowMs;
          }
          else {
              nowDate = unroundedNow;
              nowMs = unroundedNowMs;
              waitMs = 1000 * 60; // 1 minute
          }
          // there is a max setTimeout ms value (https://stackoverflow.com/a/3468650/96342)
          // ensure no longer than a day
          waitMs = Math.min(1000 * 60 * 60 * 24, waitMs);
          return {
              nowDate,
              nowMs,
              todayRange: buildDayRange(nowDate),
              waitMs,
          };
      }
      setTimeout(waitMs = this.computeTiming().waitMs) {
          // NOTE: timeout could take longer than expected if tab sleeps,
          // which is why we listen to 'visibilitychange'
          this.timeoutId = setTimeout(() => {
              // NOTE: timeout could also return *earlier* than expected, and we need to wait like 2 ms more
              // This is why use use same waitMs from computeTiming
              const timing = this.computeTiming();
              this.nowDate = timing.nowDate;
              this.nowMs = timing.nowMs;
              this.todayRange = timing.todayRange;
              this.handleChange();
              this.setTimeout(timing.waitMs);
          }, waitMs);
      }
      clearTimeout() {
          if (this.timeoutId) {
              clearTimeout(this.timeoutId);
          }
      }
  }
  /*
  The instant of `snappedMarker` (a civil rounding of the time at `rawMs`), choosing the
  occurrence on the same side of any DST transition as `rawMs` — during a fall-back fold, a
  snapped civil time exists twice. Falls back to deterministic first-occurrence resolution
  when the same-offset guess doesn't round-trip (e.g. snapping crossed the transition).
  */
  function resolveSnappedInstant(snappedMarker, rawMs, dateEnv) {
      const offsetMs = dateEnv.timestampToMarker(rawMs).valueOf() - rawMs;
      const candidateMs = snappedMarker.valueOf() - offsetMs;
      if (dateEnv.timestampToMarker(candidateMs).valueOf() === snappedMarker.valueOf()) {
          return candidateMs;
      }
      return dateEnv.toDate(snappedMarker).valueOf();
  }
  /*
  The instant of the next change to the snapped display: the next civil unit boundary, or any
  DST transition before it — at a fall-back transition the clock jumps backward onto an earlier
  unit start (no civil boundary is crossed), and waking there recomputes with fresh offsets, so
  boundaries beyond a transition never need resolving here. Scenarios (NY fall-back, hour unit):
  first fold pass (05:30Z): guess for 02:00 fails round-trip → falls back to 07:00Z; transition
  06:00Z wins. Second pass (06:30Z): guess 07:00Z round-trips; no transition ahead. Spring
  forward: the nonexistent next unit normalizes past the gap; the transition candidate fires at
  the jump itself.
  */
  function resolveNextSnappedInstant(nextUnitStart, rawMs, dateEnv) {
      const nextSnappedMs = resolveSnappedInstant(nextUnitStart, rawMs, dateEnv);
      const transitionMs = findNextOffsetTransitionMs(rawMs, dateEnv, Math.min(nextSnappedMs - rawMs, 48 * 60 * 60 * 1000));
      return transitionMs != null ? Math.min(nextSnappedMs, transitionMs) : nextSnappedMs;
  }
  // Finds the first instant whose UTC offset differs from rawMs within a short search horizon.
  function findNextOffsetTransitionMs(rawMs, dateEnv, horizonMs) {
      if (horizonMs <= 0) {
          return undefined;
      }
      const startOffsetMs = offsetAt(rawMs, dateEnv);
      let lowerMs = rawMs;
      let upperMs = rawMs + horizonMs;
      if (offsetAt(upperMs, dateEnv) === startOffsetMs) {
          return undefined;
      }
      while (upperMs - lowerMs > 1) {
          const middleMs = Math.floor((lowerMs + upperMs) / 2);
          if (offsetAt(middleMs, dateEnv) === startOffsetMs) {
              lowerMs = middleMs;
          }
          else {
              upperMs = middleMs;
          }
      }
      return upperMs > rawMs ? upperMs : undefined;
  }
  function offsetAt(instantMs, dateEnv) {
      return dateEnv.timestampToMarker(instantMs).valueOf() - instantMs;
  }
  function buildDayRange(date) {
      let start = startOfDay(date);
      let end = addDays(start, 1);
      return { start, end };
  }

  function isDimsEqual(v0, v1) {
      return v0 != null && (v0 === v1 || Math.abs(v0 - v1) < 0.01);
  }

  const nativeBorderBoxEnabled = true;
  const configMap = new Map();
  const afterSizeCallbacks = new Set();
  let isHandling = false;
  let isStalling = false;
  let isAcquiringImmediately = false;
  function afterSize(callback) {
      afterSizeCallbacks.add(callback);
      // batch & then flush when not within ResizeObserver handler loop
      // happens for watchers that die and report `null` as dimension
      if (!isHandling && !isStalling) {
          isStalling = true;
          requestAnimationFrame(() => {
              isStalling = false;
              flushAfterSize();
          });
      }
  }
  function flushAfterSize() {
      for (const flushedCallback of afterSizeCallbacks.values()) {
          afterSizeCallbacks.delete(flushedCallback);
          flushedCallback();
      }
  }
  /*
  Commits synchronously while switching every watcher registered during the
  commit to immediate acquisition: registration reads getBoundingClientRect()
  on the spot and fires the callback before returning, instead of waiting for
  the shared ResizeObserver's later delivery. This is the "measure now" path
  required when print-only DOM mounts during the native beforeprint task —
  observer delivery would arrive after the browser has already snapshotted.
  (gBCR reflects transforms while the observer's border-box does not; for
  print DOM that distinction is acceptable. Once components go functional, a
  `useElementSize`-style hook performs this same acquire-then-observe.)

  The afterSize work those callbacks (and any watcher deaths) queue
  accumulates and drains ONCE after the commit, not once per registration —
  so a commit mounting N measured wrappers costs one layout recomputation,
  not N. The drain runs in its own flushSync so handler state updates still
  settle within the calling task; additions made while draining are picked up
  by the same loop. Preact flushes mount lifecycles after the root diff, so
  the reads don't interleave with the commit's DOM writes.

  Adopt this bracket a la carte, only for commits whose entire mounted-watcher
  population tolerates a synchronous first report (currently: entering print
  mode). Ordinary watchSize callers everywhere else keep their async-first
  ResizeObserver semantics.
  */
  function flushSyncWithSizeBatching(callback) {
      const wasHandling = isHandling;
      isHandling = true;
      isAcquiringImmediately = true;
      try {
          bn(callback);
          if (!wasHandling) {
              bn(() => {
                  flushAfterSize();
                  isHandling = false; // before drain's own commit, so late afterSize calls schedule a flush
              });
          }
      }
      finally {
          isHandling = wasHandling;
          isAcquiringImmediately = false;
      }
  }
  // Native
  // -------------------------------------------------------------------------------------------------
  // Single global ResizeObserver does batching and uses less memory than individuals
  // Will always fire with delay after DOM mutation, but before repaint,
  // thus doesn't need !isHandling check like checkConfigMap
  const globalResizeObserver = typeof ResizeObserver !== 'undefined' && new ResizeObserver((entries) => {
      isHandling = true;
      // // debug
      // console.log('RESIZE-OBSERVER', entries.map((entry) => entry.target))
      for (let entry of entries) {
          const el = entry.target;
          const config = configMap.get(el);
          let width;
          let height;
          if (entry.borderBoxSize && nativeBorderBoxEnabled) {
              const borderBoxSize = entry.borderBoxSize[0] || entry.borderBoxSize; // HACK for Firefox
              width = borderBoxSize.inlineSize;
              height = borderBoxSize.blockSize;
          }
          else {
              ({ width, height } = el.getBoundingClientRect());
          }
          let shouldFire = false;
          if (!isDimsEqual(config.width, width)) {
              config.width = width;
              shouldFire = config.watchWidth;
          }
          if (!isDimsEqual(config.height, height)) {
              config.height = height;
              shouldFire || (shouldFire = config.watchHeight);
          }
          if (shouldFire) {
              config.callback(width, height);
          }
      }
      bn(() => {
          flushAfterSize();
          isHandling = false;
      });
  });
  /*
  PRECONDITION: element can only have one listener attached
  */
  function watchSize(el, callback, watchWidth = true, watchHeight = true) {
      const config = { callback, watchWidth, watchHeight };
      configMap.set(el, config);
      // within a flushSyncWithSizeBatching commit; see its comment.
      // the stored dims dedupe the observer's later initial delivery.
      if (isAcquiringImmediately) {
          const { width, height } = el.getBoundingClientRect();
          config.width = width;
          config.height = height;
          callback(width, height);
      }
      // if statement is for jsdom and other shim environments that execute component effects, but
      // haven't implemented ResizeObserver. Reference: https://github.com/jsdom/jsdom/issues/3368
      if (globalResizeObserver) {
          globalResizeObserver.observe(el, {
              box: 'border-box'
                   // default is 'content-box'
          });
      }
      return () => {
          configMap.delete(el);
          // same reasoning as above
          if (globalResizeObserver) {
              globalResizeObserver.unobserve(el);
          }
      };
  }
  function watchWidth(el, callback) {
      return watchSize(el, callback, 
      /* watchWidth = */ true);
  }
  function watchHeight(el, callback) {
      return watchSize(el, (_width, height) => callback(height), 
      /* watchWidth = */ false, 
      /* watchHeight = */ true);
  }

  class DateProfileGenerator {
      constructor(props) {
          this.props = props;
          this.initHiddenDays();
      }
      /* Date Range Computation
      ------------------------------------------------------------------------------------------------------------------*/
      // Builds a structure with info about what the dates/ranges will be for the "prev" view.
      buildPrev(currentDateProfile, currentDate, nowDate, forceToValid) {
          let { dateEnv } = this.props;
          let prevDate = dateEnv.subtract(dateEnv.startOf(currentDate, currentDateProfile.currentRangeUnit), // important for start-of-month
          currentDateProfile.dateIncrement);
          return this.build(prevDate, nowDate, -1, forceToValid);
      }
      // Builds a structure with info about what the dates/ranges will be for the "next" view.
      buildNext(currentDateProfile, currentDate, nowDate, forceToValid) {
          let { dateEnv } = this.props;
          let nextDate = dateEnv.add(dateEnv.startOf(currentDate, currentDateProfile.currentRangeUnit), // important for start-of-month
          currentDateProfile.dateIncrement);
          return this.build(nextDate, nowDate, 1, forceToValid);
      }
      // Builds a structure holding dates/ranges for rendering around the given date.
      // Optional direction param indicates whether the date is being incremented/decremented
      // from its previous value. decremented = -1, incremented = 1 (default).
      build(currentDate, nowDate, direction, forceToValid = true) {
          let { props } = this;
          let validRange;
          let currentInfo;
          let isRangeAllDay;
          let renderRange;
          let activeRange;
          let isValid;
          validRange = this.buildValidRange(nowDate);
          validRange = this.trimHiddenDays(validRange);
          if (forceToValid) {
              currentDate = constrainMarkerToRange(currentDate, validRange);
          }
          currentInfo = this.buildCurrentRangeInfo(currentDate, direction);
          isRangeAllDay = /^(year|month|week|day)$/.test(currentInfo.unit);
          renderRange = this.buildRenderRange(this.trimHiddenDays(currentInfo.range), currentInfo.unit, isRangeAllDay);
          renderRange = this.trimHiddenDays(renderRange);
          activeRange = renderRange;
          if (!props.showNonCurrentDates) {
              activeRange = intersectRanges(activeRange, currentInfo.range);
          }
          activeRange = this.adjustActiveRange(activeRange);
          activeRange = intersectRanges(activeRange, validRange); // might return null
          // it's invalid if the originally requested date is not contained,
          // or if the range is completely outside of the valid range.
          isValid = rangesIntersect(currentInfo.range, validRange);
          // HACK: constrain to render-range so `currentDate` is more useful to view rendering
          if (!rangeContainsMarker(renderRange, currentDate)) {
              currentDate = renderRange.start;
          }
          return {
              currentDate,
              // constraint for where prev/next operations can go and where events can be dragged/resized to.
              // an object with optional start and end properties.
              validRange,
              // range the view is formally responsible for.
              // for example, a month view might have 1st-31st, excluding padded dates
              currentRange: currentInfo.range,
              // name of largest unit being displayed, like "month" or "week"
              currentRangeUnit: currentInfo.unit,
              isRangeAllDay,
              // dates that display events and accept drag-n-drop
              // will be `null` if no dates accept events
              activeRange,
              // date range with a rendered skeleton
              // includes not-active days that need some sort of DOM
              renderRange,
              // Duration object that denotes the first visible time of any given day
              slotMinTime: props.slotMinTime,
              // Duration object that denotes the exclusive visible end time of any given day
              slotMaxTime: props.slotMaxTime,
              isValid,
              // how far the current date will move for a prev/next operation
              dateIncrement: this.buildDateIncrement(currentInfo.duration),
              // pass a fallback (might be null) ^
          };
      }
      // Builds an object with optional start/end properties.
      // Indicates the minimum/maximum dates to display.
      // not responsible for trimming hidden days.
      buildValidRange(nowDate) {
          let input = this.props.validRangeInput;
          let simpleInput = typeof input === 'function'
              ? input.call(this.props.calendarApi, this.props.dateEnv.toDate(nowDate))
              : input;
          return this.refineRange(simpleInput) ||
              { start: null, end: null }; // completely open-ended
      }
      // Builds a structure with info about the "current" range, the range that is
      // highlighted as being the current month for example.
      // See build() for a description of `direction`.
      // Guaranteed to have `range` and `unit` properties. `duration` is optional.
      buildCurrentRangeInfo(date, direction) {
          let { props } = this;
          let duration = null;
          let unit = null;
          let range = null;
          let dayCount;
          if (props.duration) {
              duration = props.duration;
              unit = props.durationUnit;
              range = this.buildRangeFromDuration(date, direction, duration, unit);
          }
          else if ((dayCount = this.props.dayCount)) {
              unit = 'day';
              range = this.buildRangeFromDayCount(date, direction, dayCount);
          }
          else if ((range = this.buildCustomVisibleRange(date))) {
              unit = props.dateEnv.greatestWholeUnit(range.start, range.end).unit;
          }
          else {
              duration = this.getFallbackDuration();
              unit = greatestDurationDenominator(duration).unit;
              range = this.buildRangeFromDuration(date, direction, duration, unit);
          }
          return { duration, unit, range };
      }
      getFallbackDuration() {
          return createDuration({ day: 1 });
      }
      // Returns a new activeRange to have time values (un-ambiguate)
      // slotMinTime or slotMaxTime causes the range to expand.
      adjustActiveRange(range) {
          let { dateEnv, usesMinMaxTime, slotMinTime, slotMaxTime } = this.props;
          let { start, end } = range;
          if (usesMinMaxTime) {
              // expand active range if slotMinTime is negative (why not when positive?)
              if (asRoughDays(slotMinTime) < 0) {
                  start = startOfDay(start); // necessary?
                  start = dateEnv.add(start, slotMinTime);
              }
              // expand active range if slotMaxTime is beyond one day (why not when negative?)
              if (asRoughDays(slotMaxTime) > 1) {
                  end = startOfDay(end); // necessary?
                  end = addDays(end, -1);
                  end = dateEnv.add(end, slotMaxTime);
              }
          }
          return { start, end };
      }
      // Builds the "current" range when it is specified as an explicit duration.
      // `unit` is the already-computed greatestDurationDenominator unit of duration.
      buildRangeFromDuration(date, direction, duration, unit) {
          let { dateEnv, dateAlignment } = this.props;
          let start;
          let end;
          let res;
          // compute what the alignment should be
          if (!dateAlignment) {
              let { dateIncrement } = this.props;
              if (dateIncrement) {
                  // use the smaller of the two units
                  if (asRoughMs(dateIncrement) < asRoughMs(duration)) {
                      dateAlignment = greatestDurationDenominator(dateIncrement).unit;
                  }
                  else {
                      dateAlignment = unit;
                  }
              }
              else {
                  dateAlignment = unit;
              }
          }
          // if the view displays a single day or smaller
          if (asRoughDays(duration) <= 1) {
              if (this.isHiddenDay(start)) {
                  start = this.skipHiddenDays(start, direction);
                  start = startOfDay(start);
              }
          }
          function computeRes() {
              start = dateEnv.startOf(date, dateAlignment);
              end = dateEnv.add(start, duration);
              res = { start, end };
          }
          computeRes();
          // if range is completely enveloped by hidden days, go past the hidden days
          if (!this.trimHiddenDays(res)) {
              date = this.skipHiddenDays(date, direction);
              computeRes();
          }
          return res;
      }
      // Builds the "current" range when a dayCount is specified.
      buildRangeFromDayCount(date, direction, dayCount) {
          let { dateEnv, dateAlignment } = this.props;
          let runningCount = 0;
          let start = date;
          let end;
          if (dateAlignment) {
              start = dateEnv.startOf(start, dateAlignment);
          }
          start = startOfDay(start);
          start = this.skipHiddenDays(start, direction);
          end = start;
          do {
              end = addDays(end, 1);
              if (!this.isHiddenDay(end)) {
                  runningCount += 1;
              }
          } while (runningCount < dayCount);
          return { start, end };
      }
      // Builds a normalized range object for the "visible" range,
      // which is a way to define the currentRange and activeRange at the same time.
      buildCustomVisibleRange(date) {
          let { props } = this;
          let input = props.visibleRangeInput;
          let simpleInput = typeof input === 'function'
              ? input.call(props.calendarApi, props.dateEnv.toDate(date))
              : input;
          let range = this.refineRange(simpleInput);
          if (range && (range.start == null || range.end == null)) {
              return null;
          }
          return range;
      }
      // Computes the range that will represent the element/cells for *rendering*,
      // but which may have voided days/times.
      // not responsible for trimming hidden days.
      buildRenderRange(currentRange, currentRangeUnit, isRangeAllDay) {
          return currentRange;
      }
      // Compute the duration value that should be added/substracted to the current date
      // when a prev/next operation happens.
      buildDateIncrement(fallback) {
          let { dateIncrement } = this.props;
          let customAlignment;
          if (dateIncrement) {
              return dateIncrement;
          }
          if ((customAlignment = this.props.dateAlignment)) {
              return createDuration(1, customAlignment);
          }
          if (fallback) {
              return fallback;
          }
          return createDuration({ days: 1 });
      }
      refineRange(rangeInput) {
          if (rangeInput) {
              let range = parseRange(rangeInput, this.props.dateEnv);
              if (range) {
                  range = computeVisibleDayRange(range);
              }
              return range;
          }
          return null;
      }
      /* Hidden Days
      ------------------------------------------------------------------------------------------------------------------*/
      // Initializes internal variables related to calculating hidden days-of-week
      initHiddenDays() {
          let hiddenDays = this.props.hiddenDays || []; // array of day-of-week indices that are hidden
          let isHiddenDayHash = []; // is the day-of-week hidden? (hash with day-of-week-index -> bool)
          let dayCnt = 0;
          let i;
          if (this.props.weekends === false) {
              hiddenDays.push(0, 6); // 0=sunday, 6=saturday
          }
          for (i = 0; i < 7; i += 1) {
              if (!(isHiddenDayHash[i] = hiddenDays.indexOf(i) !== -1)) {
                  dayCnt += 1;
              }
          }
          if (!dayCnt) {
              throw new Error('invalid hiddenDays'); // all days were hidden? bad.
          }
          this.isHiddenDayHash = isHiddenDayHash;
      }
      // Remove days from the beginning and end of the range that are computed as hidden.
      // If the whole range is trimmed off, returns null
      trimHiddenDays(range) {
          let { start, end } = range;
          if (start) {
              start = this.skipHiddenDays(start);
          }
          if (end) {
              end = this.skipHiddenDays(end, -1, true);
          }
          if (start == null || end == null || start < end) {
              return { start, end };
          }
          return null;
      }
      // Is the current day hidden?
      // `day` is a day-of-week index (0-6), or a Date (used for UTC)
      isHiddenDay(day) {
          if (day instanceof Date) {
              day = day.getUTCDay();
          }
          return this.isHiddenDayHash[day];
      }
      // Incrementing the current day until it is no longer a hidden day, returning a copy.
      // DOES NOT CONSIDER validRange!
      // If the initial value of `date` is not a hidden day, don't do anything.
      // Pass `isExclusive` as `true` if you are dealing with an end date.
      // `inc` defaults to `1` (increment one day forward each time)
      skipHiddenDays(date, inc = 1, isExclusive = false) {
          while (this.isHiddenDayHash[(date.getUTCDay() + (isExclusive ? inc : 0) + 7) % 7]) {
              date = addDays(date, inc);
          }
          return date;
      }
  }
  // Utils
  // -------------------------------------------------------------------------------------------------
  function computeMajorUnit(dateProfile, dateEnv) {
      const { currentRange } = dateProfile;
      if (dateProfile.currentRangeUnit === 'year') {
          if (dateEnv.diffWholeYears(currentRange.start, currentRange.end) > 1) {
              return 'year';
          }
          else {
              return 'month';
          }
      }
      else if (dateProfile.currentRangeUnit === 'month') {
          if (dateEnv.diffWholeMonths(currentRange.start, currentRange.end) > 1) {
              return 'month';
          }
      }
      else if (dateProfile.currentRangeUnit === 'week') {
          if (diffWholeWeeks(currentRange.start, currentRange.end) > 1) {
              return 'week';
          }
      }
      else if (dateProfile.currentRangeUnit === 'day') {
          if (diffWholeDays(currentRange.start, currentRange.end) > 1) {
              return 'day';
          }
      }
  }
  function isMajorUnit(dateMarker, majorUnit, dateEnv) {
      const isStartOfDay = dateMarker.valueOf() === startOfDay(dateMarker).valueOf();
      if (isStartOfDay) {
          if (majorUnit === 'year') {
              return !dateEnv.getMonth(dateMarker) && dateEnv.getDay(dateMarker) === 1;
          }
          else if (majorUnit === 'month') {
              return dateEnv.getDay(dateMarker) === 1;
          }
          else if (majorUnit === 'week') {
              return dateMarker.getUTCDay() === dateEnv.weekDow;
          }
          else if (majorUnit === 'day') {
              return true;
          }
      }
      return false;
  }

  function reduceEventStore(eventStore, action, eventSources, dateProfile, context) {
      switch (action.type) {
          case 'RECEIVE_EVENTS': // raw
              return receiveRawEvents(eventStore, eventSources[action.sourceId], action.fetchId, action.fetchRange, action.rawEvents, context);
          case 'RESET_RAW_EVENTS':
              return resetRawEvents(eventStore, eventSources[action.sourceId], action.rawEvents, dateProfile.activeRange, context);
          case 'ADD_EVENTS': // already parsed, but not expanded
              return addEvent(eventStore, action.eventStore, // new ones
              dateProfile ? dateProfile.activeRange : null, context);
          case 'RESET_EVENTS':
              return action.eventStore;
          case 'MERGE_EVENTS': // already parsed and expanded
              return mergeEventStores(eventStore, action.eventStore);
          case 'PREV': // TODO: how do we track all actions that affect dateProfile :(
          case 'NEXT':
          case 'CHANGE_DATE':
          case 'CHANGE_VIEW_TYPE':
              if (dateProfile) {
                  return expandRecurring(eventStore, dateProfile.activeRange, context);
              }
              return eventStore;
          case 'REMOVE_EVENTS':
              return excludeSubEventStore(eventStore, action.eventStore);
          case 'REMOVE_EVENT_SOURCE':
              return excludeEventsBySourceId(eventStore, action.sourceId);
          case 'REMOVE_ALL_EVENT_SOURCES':
              return filterEventStoreDefs(eventStore, (eventDef) => (!eventDef.sourceId // only keep events with no source id
              ));
          case 'REMOVE_ALL_EVENTS':
              return createEmptyEventStore();
          default:
              return eventStore;
      }
  }
  function receiveRawEvents(eventStore, eventSource, fetchId, fetchRange, rawEvents, context) {
      if (eventSource && // not already removed
          fetchId === eventSource.latestFetchId // TODO: wish this logic was always in event-sources
      ) {
          let subset = parseEvents(transformRawEvents(rawEvents, eventSource, context), eventSource, context);
          if (fetchRange) {
              subset = expandRecurring(subset, fetchRange, context);
          }
          return mergeEventStores(excludeEventsBySourceId(eventStore, eventSource.sourceId), subset);
      }
      return eventStore;
  }
  function resetRawEvents(existingEventStore, eventSource, rawEvents, activeRange, context) {
      const { defIdMap, instanceIdMap } = buildPublicIdMaps(existingEventStore);
      let newEventStore = parseEvents(transformRawEvents(rawEvents, eventSource, context), eventSource, context, false, defIdMap, instanceIdMap);
      return expandRecurring(newEventStore, activeRange, context);
  }
  function transformRawEvents(rawEvents, eventSource, context) {
      let calEachTransform = context.options.eventDataTransform;
      let sourceEachTransform = eventSource ? eventSource.eventDataTransform : null;
      if (sourceEachTransform) {
          rawEvents = transformEachRawEvent(rawEvents, sourceEachTransform);
      }
      if (calEachTransform) {
          rawEvents = transformEachRawEvent(rawEvents, calEachTransform);
      }
      return rawEvents;
  }
  function transformEachRawEvent(rawEvents, func) {
      let refinedEvents;
      if (!func) {
          refinedEvents = rawEvents;
      }
      else {
          refinedEvents = [];
          for (let rawEvent of rawEvents) {
              let refinedEvent = func(rawEvent);
              if (refinedEvent) {
                  refinedEvents.push(refinedEvent);
              }
              else if (refinedEvent == null) {
                  refinedEvents.push(rawEvent);
              } // if a different falsy value, do nothing
          }
      }
      return refinedEvents;
  }
  function addEvent(eventStore, subset, expandRange, context) {
      if (expandRange) {
          subset = expandRecurring(subset, expandRange, context);
      }
      return mergeEventStores(eventStore, subset);
  }
  function rezoneEventStoreDates(eventStore, oldDateEnv, newDateEnv) {
      let { defs } = eventStore;
      let instances = mapHash(eventStore.instances, (instance) => {
          let def = defs[instance.defId];
          if (def.allDay) {
              return instance; // isn't dependent on timezone
          }
          // markers are zone-dependent, instants are not. recompute markers FROM the exact
          // instants when present (correctly re-resolves DST-fold identity in the new zone).
          // buildValidInstanceRange re-expresses ranges the new zone's fold civilly compresses
          let { instantStartMs, instantEndMs } = instance.range;
          let start = instantStartMs != null ?
              newDateEnv.timestampToMarker(instantStartMs) :
              newDateEnv.createMarker(oldDateEnv.toDate(instance.range.start));
          let end = instantEndMs != null ?
              newDateEnv.timestampToMarker(instantEndMs) :
              newDateEnv.createMarker(oldDateEnv.toDate(instance.range.end));
          return {
              ...instance,
              range: buildValidInstanceRange({ marker: start, instantMs: instantStartMs }, { marker: end, instantMs: instantEndMs }, newDateEnv) ?? buildEventInstanceRange(
              // mixed exact/civil edges whose real order degenerated in the new zone (rare):
              // keep the exact start, apply the old real duration civilly
              start, addMs(start, getRangeInstantEndMs(instance.range, oldDateEnv) - getRangeInstantStartMs(instance.range, oldDateEnv)), instantStartMs),
          };
      });
      return { defs, instances };
  }
  function excludeEventsBySourceId(eventStore, sourceId) {
      return filterEventStoreDefs(eventStore, (eventDef) => eventDef.sourceId !== sourceId);
  }
  // QUESTION: why not just return instances? do a general object-property-exclusion util
  function excludeInstances(eventStore, removals) {
      return {
          defs: eventStore.defs,
          instances: filterHash(eventStore.instances, (instance) => !removals[instance.instanceId]),
      };
  }
  function buildPublicIdMaps(eventStore) {
      const { defs, instances } = eventStore;
      const defIdMap = {};
      const instanceIdMap = {};
      for (let defId in defs) {
          const def = defs[defId];
          const { publicId } = def;
          if (publicId) {
              defIdMap[publicId] = defId;
          }
      }
      for (let instanceId in instances) {
          const instance = instances[instanceId];
          const def = defs[instance.defId];
          const { publicId } = def;
          if (publicId) {
              instanceIdMap[publicId] = instanceId;
          }
      }
      return { defIdMap, instanceIdMap };
  }

  class Interaction {
      constructor(settings) {
          this.component = settings.component;
          this.isHitComboAllowed = settings.isHitComboAllowed || null;
      }
      destroy() {
      }
  }
  function parseInteractionSettings(component, input) {
      return {
          component,
          el: input.el,
          useEventCenter: input.useEventCenter != null ? input.useEventCenter : true,
          isHitComboAllowed: input.isHitComboAllowed || null,
      };
  }
  function interactionSettingsToStore(settings) {
      return {
          [settings.component.uid]: settings,
      };
  }
  // global state
  const interactionSettingsStore = {};

  class Emitter {
      constructor() {
          this.handlers = {};
          this.thisContext = null;
      }
      setThisContext(thisContext) {
          this.thisContext = thisContext;
      }
      setOptions(options) {
          this.options = options;
      }
      on(type, handler) {
          addToHash(this.handlers, type, handler);
      }
      off(type, handler) {
          removeFromHash(this.handlers, type, handler);
      }
      trigger(type, ...args) {
          let attachedHandlers = this.handlers[type] || [];
          let optionHandler = this.options && this.options[type];
          let handlers = [].concat(optionHandler || [], attachedHandlers);
          for (let handler of handlers) {
              handler.apply(this.thisContext, args);
          }
      }
      hasHandlers(type) {
          return Boolean((this.handlers[type] && this.handlers[type].length) ||
              (this.options && this.options[type]));
      }
  }
  function addToHash(hash, type, handler) {
      (hash[type] || (hash[type] = []))
          .push(handler);
  }
  function removeFromHash(hash, type, handler) {
      if (handler) {
          if (hash[type]) {
              hash[type] = hash[type].filter((func) => func !== handler);
          }
      }
      else {
          delete hash[type]; // remove all handler funcs for this type
      }
  }

  // TODO: easier way to add new hooks? need to update a million things
  function refinePluginDef(input) {
      return {
          name: input.name,
          premiumReleaseDate: input.premiumReleaseDate ? new Date(input.premiumReleaseDate) : undefined,
          reducers: input.reducers || [],
          isLoadingFuncs: input.isLoadingFuncs || [],
          contextInit: [].concat(input.contextInit || []),
          eventRefiners: input.eventRefiners || {},
          eventDefMemberAdders: input.eventDefMemberAdders || [],
          eventSourceRefiners: input.eventSourceRefiners || {},
          isDraggableTransformers: input.isDraggableTransformers || [],
          eventDragMutationMassagers: input.eventDragMutationMassagers || [],
          eventDefMutationAppliers: input.eventDefMutationAppliers || [],
          dateSelectionTransformers: input.dateSelectionTransformers || [],
          datePointTransforms: input.datePointTransforms || [],
          dateSpanTransforms: input.dateSpanTransforms || [],
          views: input.views || {},
          viewPropsTransformers: input.viewPropsTransformers || [],
          isPropsValid: input.isPropsValid || null,
          externalDefTransforms: input.externalDefTransforms || [],
          viewContainerAppends: input.viewContainerAppends || [],
          eventDropTransformers: input.eventDropTransformers || [],
          componentInteractions: input.componentInteractions || [],
          calendarInteractions: input.calendarInteractions || [],
          eventSourceDefs: input.eventSourceDefs || [],
          cmdFormatter: input.cmdFormatter,
          recurringTypes: input.recurringTypes || [],
          initialView: input.initialView || '',
          elementDraggingImpl: input.elementDraggingImpl,
          optionChangeHandlers: input.optionChangeHandlers || {},
          scrollerSyncerClass: input.scrollerSyncerClass || null,
          listenerRefiners: input.listenerRefiners || {},
          optionRefiners: input.optionRefiners || {},
          optionDefaults: input.optionDefaults ? [input.optionDefaults] : [],
          propSetHandlers: input.propSetHandlers || {},
      };
  }
  function buildPluginHooks(pluginDefs, globalDefs) {
      let pluginsByName = {};
      let hooks = {
          premiumReleaseDate: undefined,
          reducers: [],
          isLoadingFuncs: [],
          contextInit: [],
          eventRefiners: {},
          eventDefMemberAdders: [],
          eventSourceRefiners: {},
          isDraggableTransformers: [],
          eventDragMutationMassagers: [],
          eventDefMutationAppliers: [],
          dateSelectionTransformers: [],
          datePointTransforms: [],
          dateSpanTransforms: [],
          views: {},
          viewPropsTransformers: [],
          isPropsValid: null,
          externalDefTransforms: [],
          viewContainerAppends: [],
          eventDropTransformers: [],
          componentInteractions: [],
          calendarInteractions: [],
          eventSourceDefs: [],
          cmdFormatter: null,
          recurringTypes: [],
          initialView: '',
          elementDraggingImpl: null,
          optionChangeHandlers: {},
          scrollerSyncerClass: null,
          listenerRefiners: {},
          optionRefiners: {},
          optionDefaults: [],
          propSetHandlers: {},
      };
      /*
      IDs/names, etc
      */
      function addDefs(defs) {
          for (let unrefinedDef of defs) {
              const { name } = unrefinedDef;
              if (!name) {
                  throw new Error('Plugin must specify a name');
              }
              if (!pluginsByName[name]) {
                  const def = pluginsByName[name] = refinePluginDef(unrefinedDef);
                  hooks = combineHooks(hooks, def);
                  addDefs(unrefinedDef.deps || []);
              }
          }
      }
      if (pluginDefs) { // how could this be undefined?
          addDefs(pluginDefs);
      }
      addDefs(globalDefs); // GLOBAL plugins
      return hooks;
  }
  function buildBuildPluginHooks() {
      let currentOverrideDefs = [];
      let currentGlobalDefs = [];
      let currentHooks;
      return (overrideDefs, globalDefs) => {
          if (!currentHooks || !isArraysEqual(overrideDefs, currentOverrideDefs) || !isArraysEqual(globalDefs, currentGlobalDefs)) {
              currentHooks = buildPluginHooks(overrideDefs, globalDefs);
          }
          currentOverrideDefs = overrideDefs;
          currentGlobalDefs = globalDefs;
          return currentHooks;
      };
  }
  function combineHooks(hooks0, hooks1) {
      return {
          premiumReleaseDate: compareOptionalDates(hooks0.premiumReleaseDate, hooks1.premiumReleaseDate),
          reducers: hooks0.reducers.concat(hooks1.reducers),
          isLoadingFuncs: hooks0.isLoadingFuncs.concat(hooks1.isLoadingFuncs),
          contextInit: hooks0.contextInit.concat(hooks1.contextInit),
          eventRefiners: { ...hooks0.eventRefiners, ...hooks1.eventRefiners },
          eventDefMemberAdders: hooks0.eventDefMemberAdders.concat(hooks1.eventDefMemberAdders),
          eventSourceRefiners: { ...hooks0.eventSourceRefiners, ...hooks1.eventSourceRefiners },
          isDraggableTransformers: hooks0.isDraggableTransformers.concat(hooks1.isDraggableTransformers),
          eventDragMutationMassagers: hooks0.eventDragMutationMassagers.concat(hooks1.eventDragMutationMassagers),
          eventDefMutationAppliers: hooks0.eventDefMutationAppliers.concat(hooks1.eventDefMutationAppliers),
          dateSelectionTransformers: hooks0.dateSelectionTransformers.concat(hooks1.dateSelectionTransformers),
          datePointTransforms: hooks0.datePointTransforms.concat(hooks1.datePointTransforms),
          dateSpanTransforms: hooks0.dateSpanTransforms.concat(hooks1.dateSpanTransforms),
          views: mergeViewOptionsMap(hooks0.views, hooks1.views),
          viewPropsTransformers: hooks0.viewPropsTransformers.concat(hooks1.viewPropsTransformers),
          isPropsValid: hooks1.isPropsValid || hooks0.isPropsValid,
          externalDefTransforms: hooks0.externalDefTransforms.concat(hooks1.externalDefTransforms),
          viewContainerAppends: hooks0.viewContainerAppends.concat(hooks1.viewContainerAppends),
          eventDropTransformers: hooks0.eventDropTransformers.concat(hooks1.eventDropTransformers),
          calendarInteractions: hooks0.calendarInteractions.concat(hooks1.calendarInteractions),
          componentInteractions: hooks0.componentInteractions.concat(hooks1.componentInteractions),
          eventSourceDefs: hooks0.eventSourceDefs.concat(hooks1.eventSourceDefs),
          cmdFormatter: hooks1.cmdFormatter || hooks0.cmdFormatter,
          recurringTypes: hooks0.recurringTypes.concat(hooks1.recurringTypes),
          initialView: hooks0.initialView || hooks1.initialView, // put earlier plugins FIRST
          elementDraggingImpl: hooks0.elementDraggingImpl || hooks1.elementDraggingImpl, // "
          optionChangeHandlers: { ...hooks0.optionChangeHandlers, ...hooks1.optionChangeHandlers },
          scrollerSyncerClass: hooks0.scrollerSyncerClass || hooks1.scrollerSyncerClass,
          listenerRefiners: { ...hooks0.listenerRefiners, ...hooks1.listenerRefiners },
          optionRefiners: { ...hooks0.optionRefiners, ...hooks1.optionRefiners },
          optionDefaults: hooks0.optionDefaults.concat(hooks1.optionDefaults),
          propSetHandlers: { ...hooks0.propSetHandlers, ...hooks1.propSetHandlers },
      };
  }
  function compareOptionalDates(date0, date1) {
      if (date0 === undefined) {
          return date1;
      }
      if (date1 === undefined) {
          return date0;
      }
      return new Date(Math.max(date0.valueOf(), date1.valueOf()));
  }

  function compileViewDefs(defaultConfigs, overrideConfigs) {
      let hash = {};
      let viewType;
      for (viewType in defaultConfigs) {
          ensureViewDef(viewType, hash, defaultConfigs, overrideConfigs);
      }
      for (viewType in overrideConfigs) {
          ensureViewDef(viewType, hash, defaultConfigs, overrideConfigs);
      }
      return hash;
  }
  function ensureViewDef(viewType, hash, defaultConfigs, overrideConfigs) {
      if (hash[viewType]) {
          return hash[viewType];
      }
      let viewDef = buildViewDef(viewType, hash, defaultConfigs, overrideConfigs);
      if (viewDef) {
          hash[viewType] = viewDef;
      }
      return viewDef;
  }
  function buildViewDef(viewType, hash, defaultConfigs, overrideConfigs) {
      let defaultConfig = defaultConfigs[viewType];
      let overrideConfig = overrideConfigs[viewType];
      let queryProp = (name) => ((defaultConfig && defaultConfig[name] !== null) ? defaultConfig[name] :
          ((overrideConfig && overrideConfig[name] !== null) ? overrideConfig[name] : null));
      let theComponent = queryProp('component');
      let superType = queryProp('superType');
      let superDef = null;
      if (superType) {
          if (superType === viewType) {
              throw new Error('Can\'t have a custom view type that references itself');
          }
          superDef = ensureViewDef(superType, hash, defaultConfigs, overrideConfigs);
      }
      if (!theComponent && superDef) {
          theComponent = superDef.component;
      }
      if (!theComponent) {
          return null; // don't throw a warning, might be settings for a single-unit view
      }
      return {
          type: viewType,
          component: theComponent,
          defaults: mergeCalendarOptions(superDef ? superDef.defaults : {}, defaultConfig ? defaultConfig.rawOptions : {}),
          overrides: mergeCalendarOptions(superDef ? superDef.overrides : {}, overrideConfig ? overrideConfig.rawOptions : {}),
      };
  }

  function parseViewConfigs(inputs) {
      return mapHash(inputs, parseViewConfig);
  }
  function parseViewConfig(input) {
      let rawOptions = typeof input === 'function' ?
          { component: input } :
          input;
      let { component } = rawOptions;
      if (rawOptions.content) {
          component = createViewHookComponent(rawOptions.content);
      }
      else if (component && !(component.prototype instanceof BaseComponent)) {
          // WHY?: people were using `component` property for `content`
          // TODO: converge on one setting name
          component = createViewHookComponent(component);
      }
      return {
          superType: rawOptions.type,
          component: component,
          rawOptions, // includes type and component too :(
      };
  }
  /*
  TODO: converge with ViewContainer
  */
  function createViewHookComponent(contentGenerator) {
      return (viewProps) => (u$1(ViewContextType.Consumer, { children: (context) => {
              const { options, viewSpec } = context;
              const renderProps = {
                  // the "extra" props, for sliceEvents...
                  ...viewProps,
                  nextDayThreshold: options.nextDayThreshold,
                  // ViewDisplayInfo...
                  ...computeViewBorderless(options),
                  options: { headerToolbar: options.headerToolbar, footerToolbar: options.footerToolbar },
                  isHeightAuto: getIsHeightAuto(options),
                  view: context.viewApi,
              };
              return (u$1(ContentContainer, { tag: "div", className: joinClassNames(generateClassName(options.viewClass, renderProps), 
                  // WORKAROUND for way calendar's className would get merged into view's className
                  generateClassName(viewSpec.optionDefaults.class, renderProps), generateClassName(viewSpec.optionDefaults.className, renderProps), generateClassName(viewSpec.optionOverrides.class, renderProps), generateClassName(viewSpec.optionOverrides.className, renderProps)), renderProps: renderProps, generatorName: undefined, customGenerator: contentGenerator, didMount: options.didMount || options.viewDidMount, willUnmount: options.willUnmount || options.viewWillUnmount }));
          } }));
  }

  function buildViewSpecs(defaultInputs, optionOverrides, dynamicOptionOverrides) {
      let defaultConfigs = parseViewConfigs(defaultInputs);
      let overrideConfigs = parseViewConfigs(optionOverrides.views);
      let viewDefs = compileViewDefs(defaultConfigs, overrideConfigs);
      return mapHash(viewDefs, (viewDef) => buildViewSpec(viewDef, overrideConfigs, optionOverrides, dynamicOptionOverrides));
  }
  function buildViewSpec(viewDef, overrideConfigs, optionOverrides, dynamicOptionOverrides) {
      let durationInput = viewDef.overrides.duration ||
          viewDef.defaults.duration ||
          dynamicOptionOverrides.duration ||
          optionOverrides.duration;
      let duration = null;
      let durationUnit = '';
      let singleUnit = '';
      let singleUnitOverrides = {};
      if (durationInput) {
          duration = createDurationCached(durationInput);
          if (duration) { // valid?
              let denom = greatestDurationDenominator(duration);
              durationUnit = denom.unit;
              if (denom.value === 1) {
                  singleUnit = durationUnit;
                  singleUnitOverrides = overrideConfigs[durationUnit] ? overrideConfigs[durationUnit].rawOptions : {};
              }
          }
      }
      return {
          type: viewDef.type,
          component: viewDef.component,
          duration,
          durationUnit,
          singleUnit,
          optionDefaults: viewDef.defaults,
          optionOverrides: { ...singleUnitOverrides, ...viewDef.overrides },
      };
  }
  // hack to get memoization working
  let durationInputMap = {};
  function createDurationCached(durationInput) {
      let json = JSON.stringify(durationInput);
      let res = durationInputMap[json];
      if (res === undefined) {
          res = createDuration(durationInput);
          durationInputMap[json] = res;
      }
      return res;
  }

  function reduceViewType(viewType, action) {
      switch (action.type) {
          case 'CHANGE_VIEW_TYPE':
              viewType = action.viewType;
      }
      return viewType;
  }

  function reduceCurrentDate(currentDate, action) {
      switch (action.type) {
          case 'CHANGE_DATE':
              return action.dateMarker;
          default:
              return currentDate;
      }
  }
  // should be initialized once and stay constant
  // this will change too
  function getInitialDate(options, dateEnv, nowManager) {
      let initialDateInput = options.initialDate;
      // compute the initial ambig-timezone date
      if (initialDateInput != null) {
          return dateEnv.createMarker(initialDateInput);
      }
      return nowManager.getDateMarker();
  }

  function reduceDynamicOptionOverrides(dynamicOptionOverrides, action) {
      switch (action.type) {
          case 'SET_OPTION':
              return { ...dynamicOptionOverrides, [action.optionName]: action.rawOptionValue };
          default:
              return dynamicOptionOverrides;
      }
  }

  function reduceDateProfile(currentDateProfile, action, currentDate, nowDate, dateProfileGenerator) {
      let dp;
      switch (action.type) {
          case 'CHANGE_VIEW_TYPE':
              return dateProfileGenerator.build(action.dateMarker || currentDate, nowDate);
          case 'CHANGE_DATE':
              return dateProfileGenerator.build(action.dateMarker, nowDate);
          case 'PREV':
              dp = dateProfileGenerator.buildPrev(currentDateProfile, currentDate, nowDate);
              if (dp.isValid) {
                  return dp;
              }
              break;
          case 'NEXT':
              dp = dateProfileGenerator.buildNext(currentDateProfile, currentDate, nowDate);
              if (dp.isValid) {
                  return dp;
              }
              break;
      }
      return currentDateProfile;
  }

  function reduceDateSelection(currentSelection, action) {
      switch (action.type) {
          case 'UNSELECT_DATES':
              return null;
          case 'SELECT_DATES':
              return action.selection;
          default:
              return currentSelection;
      }
  }

  function reduceSelectedEvent(currentInstanceId, action) {
      switch (action.type) {
          case 'UNSELECT_EVENT':
              return '';
          case 'SELECT_EVENT':
              return action.eventInstanceId;
          default:
              return currentInstanceId;
      }
  }

  function reduceEventDrag(currentDrag, action) {
      let newDrag;
      switch (action.type) {
          case 'UNSET_EVENT_DRAG':
              return null;
          case 'SET_EVENT_DRAG':
              newDrag = action.state;
              return {
                  affectedEvents: newDrag.affectedEvents,
                  mutatedEvents: newDrag.mutatedEvents,
                  isEvent: newDrag.isEvent,
              };
          default:
              return currentDrag;
      }
  }

  function reduceEventResize(currentResize, action) {
      let newResize;
      switch (action.type) {
          case 'UNSET_EVENT_RESIZE':
              return null;
          case 'SET_EVENT_RESIZE':
              newResize = action.state;
              return {
                  affectedEvents: newResize.affectedEvents,
                  mutatedEvents: newResize.mutatedEvents,
                  isEvent: newResize.isEvent,
              };
          default:
              return currentResize;
      }
  }

  function parseToolbars(calendarOptions, viewSpecs, calendarApi) {
      let header = calendarOptions.headerToolbar ? parseToolbar(calendarOptions.headerToolbar, calendarOptions, viewSpecs, calendarApi) : null;
      let footer = calendarOptions.footerToolbar ? parseToolbar(calendarOptions.footerToolbar, calendarOptions, viewSpecs, calendarApi) : null;
      return { header, footer };
  }
  function parseToolbar(sectionStrHash, calendarOptions, viewSpecs, calendarApi) {
      let isRtl = calendarOptions.direction === 'rtl';
      let viewsWithButtons = [];
      let hasTitle = false;
      function processSectionStr(sectionStr) {
          let sectionRes = parseSection(sectionStr, calendarOptions, viewSpecs, calendarApi);
          viewsWithButtons.push(...sectionRes.viewsWithButtons);
          hasTitle = hasTitle || sectionRes.hasTitle;
          return sectionRes.widgets;
      }
      const sectionWidgets = {
          start: processSectionStr(sectionStrHash[isRtl ? 'right' : 'left'] || sectionStrHash.start || ''),
          center: processSectionStr(sectionStrHash.center || ''),
          end: processSectionStr(sectionStrHash[isRtl ? 'left' : 'right'] || sectionStrHash.end || ''),
      };
      return {
          sectionWidgets,
          viewsWithButtons,
          hasTitle,
      };
  }
  /*
  BAD: querying icons and text here. should be done at render time
  */
  function parseSection(sectionStr, calendarOptions, viewSpecs, calendarApi) {
      let calendarButtons = calendarOptions.buttons || {};
      let customElements = calendarOptions.toolbarElements || {};
      let sectionSubstrs = sectionStr ? sectionStr.split(' ') : [];
      let viewsWithButtons = [];
      let hasTitle = false;
      let widgets = sectionSubstrs.map((buttonGroupStr) => (buttonGroupStr.split(',').map((name) => {
          if (name === 'title') {
              hasTitle = true;
              return { name };
          }
          if (customElements[name]) {
              return { name, customElement: customElements[name] };
          }
          let viewSpec;
          let buttonInput = calendarButtons[name] || {};
          let buttonText;
          let buttonHint;
          let buttonClick;
          if ((viewSpec = viewSpecs[name])) {
              viewsWithButtons.push(name);
              const buttonTextKey = viewSpec.optionDefaults.buttonTextKey;
              buttonText = buttonInput.text ||
                  (buttonTextKey ? calendarOptions[buttonTextKey] : '') ||
                  (viewSpec.singleUnit
                      ? (calendarOptions[viewSpec.singleUnit + 'TextLong'] ||
                          calendarOptions[viewSpec.singleUnit + 'Text'])
                      : '') ||
                  name;
              /*
              buttons{}.hint(viewButtonText, viewName)
              viewHint(viewButtonText, viewName)
              */
              buttonHint = formatWithOrdinals(buttonInput.hint || calendarOptions.viewHint, [buttonText, name], // ordinal arguments
              buttonText);
              buttonClick = (ev) => {
                  buttonInput?.click?.(ev);
                  if (!ev.defaultPrevented) {
                      calendarApi.changeView(name);
                  }
              };
          }
          else {
              buttonText = buttonInput.text ||
                  calendarOptions[name + 'TextLong'] ||
                  calendarOptions[name + 'Text'] ||
                  name;
              /*
              buttons{}.hint(currentUnitText, currentUnit)
              prevHint(currentUnitUnitext, currentUnit)
              nextHint -- same
              todayHint -- same
              */
              if (name === 'prevYear') {
                  buttonHint = formatWithOrdinals(buttonInput.hint || calendarOptions.prevHint, [calendarOptions.yearText, 'year'], buttonText);
              }
              else if (name === 'nextYear') {
                  buttonHint = formatWithOrdinals(buttonInput.hint || calendarOptions.nextHint, [calendarOptions.yearText, 'year'], buttonText);
              }
              else {
                  buttonHint = (currentUnit) => {
                      return formatWithOrdinals(buttonInput.hint || calendarOptions[name + 'Hint'], // todayHint/prevHint/nextHint
                      [
                          calendarOptions[currentUnit + 'TextLong'] ||
                              calendarOptions[currentUnit + 'Text'],
                          currentUnit
                      ], buttonText);
                  };
              }
              buttonClick = (ev) => {
                  buttonInput?.click?.(ev);
                  if (!ev.defaultPrevented) {
                      calendarApi[name]?.();
                  }
              };
          }
          return {
              name,
              isView: Boolean(viewSpec),
              buttonText,
              buttonHint,
              buttonDisplay: buttonInput.display,
              buttonIconClass: buttonInput.iconClass,
              buttonIconContent: buttonInput.iconContent,
              buttonClick,
              buttonIsPrimary: buttonInput.isPrimary || false,
              buttonClass: buttonInput.class ?? buttonInput.className,
              buttonDidMount: buttonInput.didMount,
              buttonWillUnmount: buttonInput.willUnmount,
          };
      })));
      return { widgets, viewsWithButtons, hasTitle };
  }

  // always represents the current view. otherwise, it'd need to change value every time date changes
  class ViewImpl {
      constructor(type, getCurrentData, dateEnv) {
          this.type = type;
          this.getCurrentData = getCurrentData;
          this.dateEnv = dateEnv;
      }
      get calendar() {
          return this.getCurrentData().calendarApi;
      }
      get title() {
          return this.getCurrentData().viewTitle;
      }
      get activeStart() {
          return this.dateEnv.toDate(this.getCurrentData().dateProfile.activeRange.start);
      }
      get activeEnd() {
          return this.dateEnv.toDate(this.getCurrentData().dateProfile.activeRange.end);
      }
      get currentStart() {
          return this.dateEnv.toDate(this.getCurrentData().dateProfile.currentRange.start);
      }
      get currentEnd() {
          return this.dateEnv.toDate(this.getCurrentData().dateProfile.currentRange.end);
      }
      getOption(name) {
          return this.getCurrentData().options[name]; // are the view-specific options
      }
  }

  const DEF_DEFAULTS = {
      startTime: '09:00',
      endTime: '17:00',
      daysOfWeek: [1, 2, 3, 4, 5], // monday - friday
      display: 'inverse-background',
      className: '', // TODO: remove
      groupId: '_businessHours', // so multiple defs get grouped
  };
  /*
  TODO: pass around as EventDefHash!!!
  */
  function parseBusinessHours(input, context) {
      return parseEvents(refineInputs(input), null, context);
  }
  function refineInputs(input) {
      let rawDefs;
      if (input === true) {
          rawDefs = [{}]; // will get DEF_DEFAULTS verbatim
      }
      else if (Array.isArray(input)) {
          // if specifying an array, every sub-definition NEEDS a day-of-week
          rawDefs = input.filter((rawDef) => rawDef.daysOfWeek);
      }
      else if (typeof input === 'object' && input) { // non-null object
          rawDefs = [input];
      }
      else { // is probably false
          rawDefs = [];
      }
      rawDefs = rawDefs.map((rawDef) => ({ ...DEF_DEFAULTS, ...rawDef }));
      return rawDefs;
  }

  // Computes what the title at the top of the calendarApi should be for this view
  function buildTitle(dateProfile, viewOptions, dateEnv) {
      let range;
      // for views that span a large unit of time, show the proper interval, ignoring stray days before and after
      if (/^(year|month)$/.test(dateProfile.currentRangeUnit)) {
          range = dateProfile.currentRange;
      }
      else { // for day units or smaller, use the actual day range
          range = dateProfile.activeRange;
      }
      let parts;
      const options = { isEndExclusive: dateProfile.isRangeAllDay };
      if (viewOptions.titleFormat) {
          parts = dateEnv.formatRangeToParts(range.start, range.end, createFormatter(viewOptions.titleFormat), options);
      }
      else {
          parts = dateEnv.formatRangeToParts(range.start, range.end, createFormatter(buildTitleFormat(dateProfile, viewOptions.disallowAmbigTitle, 'long')), options);
          if (hasTwoMonths(parts)) {
              parts = dateEnv.formatRangeToParts(range.start, range.end, createFormatter(buildTitleFormat(dateProfile, viewOptions.disallowAmbigTitle, 'short')), options);
          }
      }
      return joinDateTimeFormatParts(parts);
  }
  // Generates the format string that should be used to generate the title for the current date range.
  // Attempts to compute the most appropriate format if not explicitly specified with `titleFormat`.
  function buildTitleFormat(dateProfile, disallowAmbigTitle, monthFormat) {
      const { currentRangeUnit } = dateProfile;
      if (currentRangeUnit === 'year') {
          return { year: 'numeric' };
      }
      if (currentRangeUnit === 'month') {
          return { year: 'numeric', month: monthFormat };
      }
      if (!disallowAmbigTitle) {
          const days = diffWholeDays(dateProfile.currentRange.start, dateProfile.currentRange.end);
          if (days !== null && days > 1) {
              return {
                  year: 'numeric',
                  month: monthFormat,
              };
          }
      }
      // one day. longer, like "September 9 2014"
      return { year: 'numeric', month: 'long', day: 'numeric' };
  }
  function hasTwoMonths(parts) {
      let hasStartMonth = false;
      let hasEndMonth = false;
      for (const part of parts) {
          if (part.type === 'month') {
              if (part.source === 'startRange')
                  hasStartMonth = true;
              if (part.source === 'endRange')
                  hasEndMonth = true;
          }
      }
      return hasStartMonth && hasEndMonth;
  }

  /*
  TODO: test switching timezones when NO timezone plugin
  */
  class CalendarNowManager {
      constructor() {
          this.resetListeners = new Set();
      }
      handleInput(dateEnv, // will change if timezone setup changed
      nowInput) {
          const oldDateEnv = this.dateEnv;
          if (dateEnv !== oldDateEnv) {
              if (typeof nowInput === 'function') {
                  this.nowFn = nowInput;
              }
              else if (!oldDateEnv) { // first time?
                  // inputs that express an exact instant (ISO with offset, Date, epoch ms) keep their
                  // exact epoch (marker round-trips are ambiguous during DST folds). civil inputs
                  // resolve deterministically to the first occurrence.
                  this.nowAnchorDate = nowInput
                      ? resolveInputToDate(nowInput, dateEnv)
                      : new Date();
                  this.nowAnchorQueried = Date.now();
              }
              this.dateEnv = dateEnv;
              // not first time? fire reset handlers
              if (oldDateEnv) {
                  for (const resetListener of this.resetListeners.values()) {
                      resetListener();
                  }
              }
          }
      }
      getDateMarker() {
          return this.dateEnv.timestampToMarker(this.getEpochMs());
      }
      /*
      The exact instant of "now". Unlike a DateMarker, unambiguous during DST transitions.
      When `now` was supplied as a function returning a civil time, resolves deterministically.
      */
      getEpochMs() {
          return this.nowAnchorDate
              ? this.nowAnchorDate.valueOf() + (Date.now() - this.nowAnchorQueried)
              : resolveInputToDate(this.nowFn(), this.dateEnv).valueOf();
      }
      addResetListener(handler) {
          this.resetListeners.add(handler);
      }
      removeResetListener(handler) {
          this.resetListeners.delete(handler);
      }
  }
  /*
  Resolves a date input to an exact-instant Date. Prefers the instant the input itself
  expressed (unambiguous during DST folds); falls back to first-occurrence resolution.
  */
  function resolveInputToDate(input, dateEnv) {
      const meta = dateEnv.createMarkerMeta(input);
      return meta.instantMs != null
          ? new Date(meta.instantMs)
          : dateEnv.toDate(meta.marker);
  }

  class CalendarDataManager {
      constructor(config) {
          this.computeCurrentViewData = memoize(this._computeCurrentViewData);
          this.organizeRawLocales = memoize(organizeRawLocales);
          this.buildLocale = memoize(buildLocale);
          this.buildPluginHooks = buildBuildPluginHooks();
          this.buildDateEnv = memoize(buildDateEnv$1);
          this.parseToolbars = memoize(parseToolbars);
          this.buildViewSpecs = memoize(buildViewSpecs);
          this.buildDateProfileGenerator = memoizeObjArg(buildDateProfileGenerator);
          this.buildViewApi = memoize(buildViewApi);
          this.buildViewUiProps = memoizeObjArg(buildViewUiProps);
          this.buildEventUiBySource = memoize(buildEventUiBySource, isPropsEqualShallow);
          this.buildEventUiBases = memoize(buildEventUiBases);
          this.parseContextBusinessHours = memoizeObjArg(parseContextBusinessHours);
          this.buildToolbarProps = memoize(buildToolbarProps);
          this.buildTitle = memoize(buildTitle);
          this.nowManager = new CalendarNowManager();
          this.isDrainingActionQueue = false;
          this.actionQueue = [];
          this.optionOverrides = {};
          // used by CalendarApiImpl
          this.emitter = new Emitter();
          this.currentCalendarOptionsRefiners = {};
          this.currentCalendarOptionsInput = {};
          this.currentCalendarOptionsRefined = {};
          this.currentViewOptionsInput = {};
          this.currentViewOptionsRefined = {};
          this.optionsForRefining = [];
          this.optionsForHandling = [];
          this.getCurrentData = () => this.data;
          this.handleNowChange = () => {
              this.dispatch({ type: 'UPDATE_NOW' });
          };
          this.dispatch = (action) => {
              this.actionQueue.push(action);
              if (!this.isDrainingActionQueue) {
                  this.drainActionQueue();
              }
          };
          this.config = config;
          this.nowManager = new CalendarNowManager();
          this.nowTimer = new NowTimerRunner(this.handleNowChange);
      }
      destroy() {
          this.nowTimer.destroy();
      }
      /*
      Will NOT trigger onDataChange unless there were other actions in the queue
      */
      update(optionOverrides) {
          this.optionOverrides = optionOverrides;
          this.actionQueue.push({ type: 'IDLE' }); // ensure reducer gets called
          this.drainActionQueue();
          return this.data;
      }
      /*
      WILL trigger onDataChange
      */
      resetOptions(optionOverrides, changedOptionNames) {
          if (changedOptionNames === undefined) {
              this.optionOverrides = optionOverrides;
          }
          else {
              this.optionOverrides = { ...this.optionOverrides, ...optionOverrides };
              this.optionsForRefining.push(...changedOptionNames);
          }
          this.dispatch({ type: 'RESET_OPTIONS' });
      }
      drainActionQueue() {
          let calendarContext;
          let { state, data } = this;
          const isInit = !state;
          const { actionQueue } = this;
          const actionsComplete = []; // non-idle
          this.isDrainingActionQueue = true;
          while (actionQueue.length) {
              const action = actionQueue.shift();
              ({ state, data, calendarContext } = this.reduce(state, data, action));
              this.state = state;
              this.data = data;
              if (action.type !== 'IDLE') {
                  actionsComplete.push(action);
              }
          }
          this.isDrainingActionQueue = false;
          if (isInit) {
              const controllerOption = calendarContext.options.controller;
              if (controllerOption) {
                  controllerOption._setApi(this.config.calendarApi);
              }
          }
          if (!isInit && actionsComplete.length) {
              const { onDataChange } = this.config;
              if (onDataChange) {
                  onDataChange(this.data, actionsComplete);
              }
          }
      }
      reduce(prevState, prevData, action) {
          let { config } = this;
          let isInit = !prevState;
          // === Compute options and view data ===
          let dynamicOptionOverrides = isInit
              ? {}
              : reduceDynamicOptionOverrides(prevState.dynamicOptionOverrides, action);
          let optionsData = this.computeOptionsData(this.optionOverrides, dynamicOptionOverrides, config.calendarApi);
          let currentViewType = isInit
              ? (optionsData.calendarOptions.initialView || optionsData.pluginHooks.initialView)
              : reduceViewType(prevState.currentViewType, action);
          let currentViewData = this.computeCurrentViewData(currentViewType, optionsData, this.optionOverrides, dynamicOptionOverrides);
          // === Wire things up ===
          config.calendarApi.currentDataManager = this;
          this.emitter.setThisContext(config.calendarApi);
          this.emitter.setOptions(currentViewData.options);
          // === Build calendarContext ===
          let calendarContext = {
              nowManager: this.nowManager,
              dateEnv: optionsData.dateEnv,
              options: optionsData.calendarOptions,
              pluginHooks: optionsData.pluginHooks,
              calendarApi: config.calendarApi,
              dispatch: this.dispatch,
              emitter: this.emitter,
              getCurrentData: this.getCurrentData,
          };
          // === Update now timer ===
          let { nowDate } = this.nowTimer.update({
              unit: 'day',
              unitValue: 1,
              nowIndicatorSnap: 'auto',
              nowManager: this.nowManager,
              dateEnv: optionsData.dateEnv,
          });
          // === Compute currentDate ===
          let currentDate = isInit
              ? getInitialDate(optionsData.calendarOptions, optionsData.dateEnv, this.nowManager)
              : reduceCurrentDate(prevState.currentDate, action);
          // === Compute dateProfile ===
          let dateProfile;
          if (isInit) {
              dateProfile = currentViewData.dateProfileGenerator.build(currentDate, nowDate);
          }
          else {
              dateProfile = prevState.dateProfile;
              // Check for generator change
              if (prevData && prevData.dateProfileGenerator !== currentViewData.dateProfileGenerator) {
                  dateProfile = currentViewData.dateProfileGenerator.build(currentDate, nowDate);
              }
              dateProfile = reduceDateProfile(dateProfile, action, currentDate, nowDate, currentViewData.dateProfileGenerator);
          }
          // === Adjust currentDate if out of range ===
          if ((action && (action.type === 'PREV' || action.type === 'NEXT')) ||
              !rangeContainsMarker(dateProfile.activeRange, currentDate)) {
              currentDate = dateProfile.currentRange.start;
          }
          // === Compute eventSources, eventStore ===
          let eventSources = isInit
              ? initEventSources(optionsData.calendarOptions, dateProfile, calendarContext)
              : reduceEventSources(prevState.eventSources, action, dateProfile, calendarContext);
          let eventStore = isInit
              ? createEmptyEventStore()
              : reduceEventStore(prevState.eventStore, action, eventSources, dateProfile, calendarContext);
          // === Compute renderableEventStore ===
          let isEventsLoading = computeEventSourcesLoading(eventSources);
          let renderableEventStore = isInit
              ? createEmptyEventStore()
              : (isEventsLoading && !currentViewData.options.progressiveEventRendering)
                  ? (prevState.renderableEventStore || eventStore)
                  : eventStore;
          // === UI computation ===
          let { eventUiSingleBase, selectionConfig } = this.buildViewUiProps(calendarContext);
          let eventUiBySource = this.buildEventUiBySource(eventSources);
          let eventUiBases = isInit
              ? {}
              : this.buildEventUiBases(renderableEventStore.defs, eventUiSingleBase, eventUiBySource);
          // === Build new state ===
          let newState = {
              dynamicOptionOverrides,
              currentViewType,
              currentDate,
              dateProfile,
              eventSources,
              eventStore,
              renderableEventStore,
              selectionConfig,
              eventUiBases,
              businessHours: this.parseContextBusinessHours(calendarContext),
              dateSelection: isInit ? null : reduceDateSelection(prevState.dateSelection, action),
              eventSelection: isInit ? '' : reduceSelectedEvent(prevState.eventSelection, action),
              eventDrag: isInit ? null : reduceEventDrag(prevState.eventDrag, action),
              eventResize: isInit ? null : reduceEventResize(prevState.eventResize, action),
              nowDate,
          };
          // === Plugin reducers ===
          let contextAndState = { ...calendarContext, ...newState };
          for (let reducer of optionsData.pluginHooks.reducers) {
              Object.assign(newState, reducer(prevState, action, contextAndState));
          }
          // === Loading state emission ===
          let wasLoading = prevState ? computeIsLoading(prevState, calendarContext) : false;
          let isLoading = computeIsLoading(newState, calendarContext);
          if (!wasLoading && isLoading) {
              this.emitter.trigger('loading', true);
          }
          else if (wasLoading && !isLoading) {
              this.emitter.trigger('loading', false);
          }
          // === Build CalendarData ===
          let viewTitle = this.buildTitle(dateProfile, currentViewData.options, optionsData.dateEnv);
          let toolbarProps = this.buildToolbarProps(currentViewData.viewSpec, dateProfile, currentViewData.dateProfileGenerator, currentDate, nowDate, viewTitle);
          let newData = {
              viewTitle,
              nowManager: this.nowManager,
              calendarApi: config.calendarApi,
              dispatch: this.dispatch,
              emitter: this.emitter,
              getCurrentData: this.getCurrentData,
              toolbarProps,
              ...optionsData,
              ...currentViewData,
              ...newState,
          };
          // === Handle option changes ===
          let changeHandlers = optionsData.pluginHooks.optionChangeHandlers;
          let prevCalendarOptions = prevData && prevData.calendarOptions;
          let newCalendarOptions = optionsData.calendarOptions;
          if (prevCalendarOptions && prevCalendarOptions !== newCalendarOptions) {
              if (prevCalendarOptions.timeZone !== newCalendarOptions.timeZone) {
                  // HACK
                  newState.eventSources = newData.eventSources = reduceEventSourcesNewTimeZone(newData.eventSources, dateProfile, newData);
                  newState.eventStore = newData.eventStore = rezoneEventStoreDates(newData.eventStore, prevData.dateEnv, newData.dateEnv);
                  newState.renderableEventStore = newData.renderableEventStore = rezoneEventStoreDates(newData.renderableEventStore, prevData.dateEnv, newData.dateEnv);
              }
              for (let optionName in changeHandlers) {
                  if (this.optionsForHandling.indexOf(optionName) !== -1 ||
                      prevCalendarOptions[optionName] !== newCalendarOptions[optionName]) {
                      changeHandlers[optionName](newCalendarOptions[optionName], newData);
                  }
              }
          }
          this.optionsForHandling = [];
          return { state: newState, data: newData, calendarContext };
      }
      computeOptionsData(optionOverrides, dynamicOptionOverrides, calendarApi) {
          // TODO: blacklist options that are handled by optionChangeHandlers
          if (!this.optionsForRefining.length &&
              optionOverrides === this.stableOptionOverrides &&
              dynamicOptionOverrides === this.stableDynamicOptionOverrides) {
              return this.stableCalendarOptionsData;
          }
          let { refinedOptions, pluginHooks, localeDefaults, availableLocaleData, } = this.processRawCalendarOptions(optionOverrides, dynamicOptionOverrides);
          let dateEnv = this.buildDateEnv(refinedOptions.timeZone, refinedOptions.locale, refinedOptions.weekNumberCalculation, refinedOptions.firstDay, refinedOptions.weekTextLong, refinedOptions.weekTextShort, pluginHooks, availableLocaleData);
          let viewSpecs = this.buildViewSpecs(pluginHooks.views, this.stableOptionOverrides, this.stableDynamicOptionOverrides);
          let toolbarConfig = this.parseToolbars(refinedOptions, viewSpecs, calendarApi);
          return this.stableCalendarOptionsData = {
              calendarOptions: refinedOptions,
              pluginHooks,
              dateEnv,
              viewSpecs,
              toolbarConfig,
              localeDefaults,
              availableRawLocales: availableLocaleData.map,
          };
      }
      // always called from behind a memoizer
      processRawCalendarOptions(optionOverrides, dynamicOptionOverrides) {
          let { locales, locale } = mergeCalendarOptions(BASE_OPTION_DEFAULTS, optionOverrides, dynamicOptionOverrides);
          let availableLocaleData = this.organizeRawLocales(locales);
          let availableRawLocales = availableLocaleData.map;
          let localeDefaults = this.buildLocale(locale || availableLocaleData.defaultCode, availableRawLocales).options;
          let pluginHooks = this.buildPluginHooks(optionOverrides.plugins || [], globalPlugins);
          let refiners = this.currentCalendarOptionsRefiners = {
              ...BASE_OPTION_REFINERS,
              ...CALENDAR_LISTENER_REFINERS,
              ...CALENDAR_ONLY_OPTION_REFINERS,
              ...pluginHooks.listenerRefiners,
              ...pluginHooks.optionRefiners,
          };
          let raw = mergeCalendarOptions(BASE_OPTION_DEFAULTS, ...pluginHooks.optionDefaults, localeDefaults, filterKnownOptions(mergeCalendarOptions(optionOverrides, dynamicOptionOverrides), refiners));
          let refined = {};
          let currentRaw = this.currentCalendarOptionsInput;
          let currentRefined = this.currentCalendarOptionsRefined;
          let anyChanges = false;
          for (let optionName in raw) {
              if (this.optionsForRefining.indexOf(optionName) === -1 && (raw[optionName] === currentRaw[optionName] || (COMPLEX_OPTION_COMPARATORS[optionName] &&
                  (optionName in currentRaw) &&
                  COMPLEX_OPTION_COMPARATORS[optionName](currentRaw[optionName], raw[optionName])) || isMergedPropsEqual(currentRaw[optionName], raw[optionName]))) {
                  refined[optionName] = currentRefined[optionName];
              }
              else if (refiners[optionName]) {
                  refined[optionName] = refiners[optionName](raw[optionName], optionName);
                  anyChanges = true;
              }
          }
          if (anyChanges) {
              this.currentCalendarOptionsInput = raw;
              this.currentCalendarOptionsRefined = refined;
              this.stableOptionOverrides = optionOverrides;
              this.stableDynamicOptionOverrides = dynamicOptionOverrides;
          }
          this.optionsForHandling.push(...this.optionsForRefining);
          this.optionsForRefining = [];
          return {
              rawOptions: this.currentCalendarOptionsInput,
              refinedOptions: this.currentCalendarOptionsRefined,
              pluginHooks,
              availableLocaleData,
              localeDefaults,
          };
      }
      _computeCurrentViewData(viewType, optionsData, optionOverrides, dynamicOptionOverrides) {
          let viewSpec = optionsData.viewSpecs[viewType];
          if (!viewSpec) {
              throw new Error(`viewType "${viewType}" is not available. Please make sure you've loaded all neccessary plugins`);
          }
          let { refinedOptions } = this.processRawViewOptions(viewSpec, optionsData.pluginHooks, optionsData.localeDefaults, optionOverrides, dynamicOptionOverrides);
          this.nowManager.handleInput(optionsData.dateEnv, refinedOptions.now);
          let dateProfileGenerator = this.buildDateProfileGenerator({
              dateProfileGeneratorClass: viewSpec.optionDefaults.dateProfileGeneratorClass,
              duration: viewSpec.duration,
              durationUnit: viewSpec.durationUnit,
              usesMinMaxTime: viewSpec.optionDefaults.usesMinMaxTime,
              dateEnv: optionsData.dateEnv,
              calendarApi: this.config.calendarApi,
              slotMinTime: refinedOptions.slotMinTime,
              slotMaxTime: refinedOptions.slotMaxTime,
              showNonCurrentDates: refinedOptions.showNonCurrentDates,
              dayCount: refinedOptions.dayCount,
              dateAlignment: refinedOptions.dateAlignment,
              dateIncrement: refinedOptions.dateIncrement,
              hiddenDays: refinedOptions.hiddenDays,
              weekends: refinedOptions.weekends,
              validRangeInput: refinedOptions.validRange,
              visibleRangeInput: refinedOptions.visibleRange,
              fixedWeekCount: refinedOptions.fixedWeekCount,
          });
          let viewApi = this.buildViewApi(viewType, this.getCurrentData, optionsData.dateEnv);
          return { viewSpec, options: refinedOptions, dateProfileGenerator, viewApi };
      }
      processRawViewOptions(viewSpec, pluginHooks, localeDefaults, optionOverrides, dynamicOptionOverrides) {
          let refiners = {
              ...BASE_OPTION_REFINERS,
              ...CALENDAR_LISTENER_REFINERS,
              ...CALENDAR_ONLY_OPTION_REFINERS,
              ...VIEW_ONLY_OPTION_REFINERS,
              ...pluginHooks.listenerRefiners,
              ...pluginHooks.optionRefiners,
          };
          let raw = mergeCalendarOptions(BASE_OPTION_DEFAULTS, ...pluginHooks.optionDefaults, viewSpec.optionDefaults, localeDefaults, filterKnownOptions(mergeCalendarOptions(optionOverrides, viewSpec.optionOverrides, dynamicOptionOverrides), refiners));
          let refined = {};
          let currentRaw = this.currentViewOptionsInput;
          let currentRefined = this.currentViewOptionsRefined;
          let anyChanges = false;
          for (let optionName in raw) {
              if (raw[optionName] === currentRaw[optionName] || (COMPLEX_OPTION_COMPARATORS[optionName] &&
                  COMPLEX_OPTION_COMPARATORS[optionName](raw[optionName], currentRaw[optionName])) || isMergedPropsEqual(currentRaw[optionName], raw[optionName])) {
                  refined[optionName] = currentRefined[optionName];
              }
              else {
                  if (raw[optionName] === this.currentCalendarOptionsInput[optionName] ||
                      (COMPLEX_OPTION_COMPARATORS[optionName] &&
                          COMPLEX_OPTION_COMPARATORS[optionName](raw[optionName], this.currentCalendarOptionsInput[optionName]))) {
                      if (optionName in this.currentCalendarOptionsRefined) { // might be an "extra" prop
                          refined[optionName] = this.currentCalendarOptionsRefined[optionName];
                      }
                  }
                  else if (refiners[optionName]) {
                      refined[optionName] = refiners[optionName](raw[optionName], optionName);
                  }
                  anyChanges = true;
              }
          }
          if (anyChanges) {
              this.currentViewOptionsInput = raw;
              this.currentViewOptionsRefined = refined;
          }
          return {
              rawOptions: this.currentViewOptionsInput,
              refinedOptions: this.currentViewOptionsRefined,
          };
      }
  }
  function buildDateEnv$1(timeZone, explicitLocale, weekNumberCalculation, firstDay, weekTextLong, weekTextShort, pluginHooks, availableLocaleData) {
      let locale = buildLocale(explicitLocale || availableLocaleData.defaultCode, availableLocaleData.map);
      return new DateEnv({
          calendarSystem: 'gregory', // TODO: make this a setting
          timeZone,
          locale,
          weekNumberCalculation,
          firstDay,
          weekTextLong,
          weekTextShort,
          cmdFormatter: pluginHooks.cmdFormatter,
      });
  }
  function buildDateProfileGenerator(props) {
      let DateProfileGeneratorClass = props.dateProfileGeneratorClass || DateProfileGenerator;
      return new DateProfileGeneratorClass(props);
  }
  function buildViewApi(type, getCurrentData, dateEnv) {
      return new ViewImpl(type, getCurrentData, dateEnv);
  }
  function buildEventUiBySource(eventSources) {
      return mapHash(eventSources, (eventSource) => eventSource.ui);
  }
  /*
  The result of this is processed by compileEventUi
  */
  function buildEventUiBases(eventDefs, eventUiSingleBase, eventUiBySource) {
      let eventUiBases = {
          '': eventUiSingleBase, // fallback
      };
      for (let defId in eventDefs) {
          let def = eventDefs[defId];
          if (def.sourceId && eventUiBySource[def.sourceId]) {
              eventUiBases[defId] = eventUiBySource[def.sourceId];
          }
      }
      return eventUiBases;
  }
  function buildViewUiProps(calendarContext) {
      const { options } = calendarContext;
      return {
          eventUiSingleBase: createEventUi({
              display: options.eventDisplay,
              editable: options.editable, // without "event" at start
              startEditable: options.eventStartEditable,
              durationEditable: options.eventDurationEditable,
              constraint: options.eventConstraint,
              overlap: typeof options.eventOverlap === 'boolean' ? options.eventOverlap : undefined,
              allow: options.eventAllow,
              // color: options.eventColor, // StandardEvent/BgEvent will handle this
              // contrastColor: options.eventContrastColor, // StandardEvent/BgEvent will handle this
              // className: options.eventClass // render hook will handle this
          }, calendarContext),
          selectionConfig: createEventUi({
              constraint: options.selectConstraint,
              overlap: typeof options.selectOverlap === 'boolean' ? options.selectOverlap : undefined,
              allow: options.selectAllow,
          }, calendarContext),
      };
  }
  function computeIsLoading(state, context) {
      for (let isLoadingFunc of context.pluginHooks.isLoadingFuncs) {
          if (isLoadingFunc(state)) {
              return true;
          }
      }
      return false;
  }
  function parseContextBusinessHours(calendarContext) {
      return parseBusinessHours(calendarContext.options.businessHours, calendarContext);
  }
  const warnedUnknownOptions = {};
  function filterKnownOptions(options, optionRefiners) {
      const knownOptions = {};
      for (const optionName in options) {
          if (optionRefiners[optionName]) {
              knownOptions[optionName] = options[optionName];
          }
          else if (!warnedUnknownOptions[optionName]) {
              warn(`Unknown option \`${optionName}\`.`);
              warnedUnknownOptions[optionName] = true;
          }
      }
      return knownOptions;
  }
  function buildToolbarProps(viewSpec, dateProfile, dateProfileGenerator, currentDate, nowDate, title) {
      // don't force any date-profiles to valid date profiles (the `false`) so that we can tell if it's invalid
      let todayInfo = dateProfileGenerator.build(nowDate, nowDate, undefined, /* forceToValid = */ false);
      let prevInfo = dateProfileGenerator.buildPrev(dateProfile, currentDate, nowDate, /* forceToValid = */ false);
      let nextInfo = dateProfileGenerator.buildNext(dateProfile, currentDate, nowDate, /* forceToValid = */ false);
      return {
          title,
          selectedButton: viewSpec.type,
          navUnit: viewSpec.singleUnit,
          isTodayEnabled: todayInfo.isValid && !rangeContainsMarker(dateProfile.currentRange, nowDate),
          isPrevEnabled: prevInfo.isValid,
          isNextEnabled: nextInfo.isValid,
      };
  }

  class CalendarApiImpl {
      getCurrentData() {
          return this.currentDataManager.getCurrentData();
      }
      dispatch(action) {
          this.currentDataManager.dispatch(action);
      }
      get view() { return this.getCurrentData().viewApi; }
      batchRendering(callback) {
          callback();
      }
      // Options
      // -----------------------------------------------------------------------------------------------------------------
      setOption(name, val) {
          this.dispatch({
              type: 'SET_OPTION',
              optionName: name,
              rawOptionValue: val,
          });
      }
      getOption(name) {
          return this.currentDataManager.currentCalendarOptionsInput[name];
      }
      getAvailableLocaleCodes() {
          return Object.keys(this.getCurrentData().availableRawLocales);
      }
      // Trigger
      // -----------------------------------------------------------------------------------------------------------------
      on(handlerName, handler) {
          let { currentDataManager } = this;
          if (currentDataManager.currentCalendarOptionsRefiners[handlerName]) {
              currentDataManager.emitter.on(handlerName, handler);
          }
          else {
              warn(`Unknown listener \`${handlerName}\`.`);
          }
      }
      off(handlerName, handler) {
          this.currentDataManager.emitter.off(handlerName, handler);
      }
      // not meant for public use
      trigger(handlerName, ...args) {
          this.currentDataManager.emitter.trigger(handlerName, ...args);
      }
      // View
      // -----------------------------------------------------------------------------------------------------------------
      changeView(viewType, dateOrRange) {
          this.batchRendering(() => {
              this.unselect();
              if (dateOrRange) {
                  if (dateOrRange.start && dateOrRange.end) { // a range
                      this.dispatch({
                          type: 'CHANGE_VIEW_TYPE',
                          viewType,
                      });
                      this.dispatch({
                          type: 'SET_OPTION',
                          optionName: 'visibleRange',
                          rawOptionValue: dateOrRange,
                      });
                  }
                  else {
                      let { dateEnv } = this.getCurrentData();
                      this.dispatch({
                          type: 'CHANGE_VIEW_TYPE',
                          viewType,
                          dateMarker: dateEnv.createMarker(dateOrRange),
                      });
                  }
              }
              else {
                  this.dispatch({
                      type: 'CHANGE_VIEW_TYPE',
                      viewType,
                  });
              }
          });
      }
      // Forces navigation to a view for the given date.
      // `viewType` can be a specific view name or a generic one like "week" or "day".
      // needs to change
      zoomTo(dateMarker, viewType) {
          let state = this.getCurrentData();
          let spec;
          viewType = viewType || 'day'; // day is default zoom
          spec = state.viewSpecs[viewType] || this.getUnitViewSpec(viewType);
          this.unselect();
          if (spec) {
              this.dispatch({
                  type: 'CHANGE_VIEW_TYPE',
                  viewType: spec.type,
                  dateMarker,
              });
          }
          else {
              this.dispatch({
                  type: 'CHANGE_DATE',
                  dateMarker,
              });
          }
      }
      // Given a duration singular unit, like "week" or "day", finds a matching view spec.
      // Preference is given to views that have corresponding buttons.
      getUnitViewSpec(unit) {
          let { viewSpecs, toolbarConfig } = this.getCurrentData();
          let viewTypes = [].concat(toolbarConfig.header ? toolbarConfig.header.viewsWithButtons : [], toolbarConfig.footer ? toolbarConfig.footer.viewsWithButtons : []);
          let i;
          let spec;
          for (let viewType in viewSpecs) {
              viewTypes.push(viewType);
          }
          for (i = 0; i < viewTypes.length; i += 1) {
              spec = viewSpecs[viewTypes[i]];
              if (spec) {
                  if (spec.singleUnit === unit) {
                      return spec;
                  }
              }
          }
          return null;
      }
      // Current Date
      // -----------------------------------------------------------------------------------------------------------------
      prev() {
          this.unselect();
          this.dispatch({ type: 'PREV' });
      }
      next() {
          this.unselect();
          this.dispatch({ type: 'NEXT' });
      }
      prevYear() {
          let state = this.getCurrentData();
          this.unselect();
          this.dispatch({
              type: 'CHANGE_DATE',
              dateMarker: state.dateEnv.addYears(state.currentDate, -1),
          });
      }
      nextYear() {
          let state = this.getCurrentData();
          this.unselect();
          this.dispatch({
              type: 'CHANGE_DATE',
              dateMarker: state.dateEnv.addYears(state.currentDate, 1),
          });
      }
      today() {
          let state = this.getCurrentData();
          this.unselect();
          this.dispatch({
              type: 'CHANGE_DATE',
              dateMarker: state.nowManager.getDateMarker(),
          });
      }
      gotoDate(zonedDateInput) {
          let state = this.getCurrentData();
          this.unselect();
          this.dispatch({
              type: 'CHANGE_DATE',
              dateMarker: state.dateEnv.createMarker(zonedDateInput),
          });
      }
      incrementDate(deltaInput) {
          let state = this.getCurrentData();
          let delta = createDuration(deltaInput);
          if (delta) { // else, warn about invalid input?
              this.unselect();
              this.dispatch({
                  type: 'CHANGE_DATE',
                  dateMarker: state.dateEnv.add(state.currentDate, delta),
              });
          }
      }
      getDate() {
          let state = this.getCurrentData();
          return state.dateEnv.toDate(state.currentDate);
      }
      // Date Formatting Utils
      // -----------------------------------------------------------------------------------------------------------------
      formatDate(d, formatter) {
          let { dateEnv } = this.getCurrentData();
          let dateMeta = dateEnv.createMarkerMeta(d);
          return joinDateTimeFormatParts(dateEnv.formatToParts(dateMeta.marker, createFormatter(formatter), { instantMs: dateMeta.instantMs }));
      }
      // `settings` is for formatter AND isEndExclusive
      formatRange(d0, d1, settings) {
          let { dateEnv } = this.getCurrentData();
          let startMeta = dateEnv.createMarkerMeta(d0);
          let endMeta = dateEnv.createMarkerMeta(d1);
          return joinDateTimeFormatParts(dateEnv.formatRangeToParts(startMeta.marker, endMeta.marker, createFormatter(settings), {
              isEndExclusive: settings.isEndExclusive,
              startInstantMs: startMeta.instantMs,
              endInstantMs: endMeta.instantMs,
          }));
      }
      formatIso(d, omitTime) {
          let { dateEnv } = this.getCurrentData();
          return dateEnv.formatIso(dateEnv.createMarker(d), { omitTime });
      }
      // Date Selection / Event Selection / DayClick
      // -----------------------------------------------------------------------------------------------------------------
      select(dateOrObj, endDate) {
          let selectionInput;
          if (endDate == null) {
              if (dateOrObj.start != null) {
                  selectionInput = dateOrObj;
              }
              else {
                  selectionInput = {
                      start: dateOrObj,
                      end: null,
                  };
              }
          }
          else {
              selectionInput = {
                  start: dateOrObj,
                  end: endDate,
              };
          }
          let state = this.getCurrentData();
          let selection = parseDateSpan(selectionInput, state.dateEnv, createDuration({ days: 1 }));
          if (selection) { // throw parse error otherwise?
              this.dispatch({ type: 'SELECT_DATES', selection });
              triggerDateSelect(selection, null, state);
          }
      }
      unselect(pev) {
          let state = this.getCurrentData();
          if (state.dateSelection) {
              this.dispatch({ type: 'UNSELECT_DATES' });
              triggerDateUnselect(pev, state);
          }
      }
      // Public Events API
      // -----------------------------------------------------------------------------------------------------------------
      addEvent(eventInput, sourceInput) {
          if (eventInput instanceof EventImpl) {
              let def = eventInput._def;
              let instance = eventInput._instance;
              let currentData = this.getCurrentData();
              // not already present? don't want to add an old snapshot
              if (!currentData.eventStore.defs[def.defId]) {
                  this.dispatch({
                      type: 'ADD_EVENTS',
                      eventStore: eventTupleToStore({ def, instance }), // TODO: better util for two args?
                  });
                  this.triggerEventAdd(eventInput);
              }
              return eventInput;
          }
          let state = this.getCurrentData();
          let eventSource;
          if (sourceInput instanceof EventSourceImpl) {
              eventSource = sourceInput.internalEventSource;
          }
          else if (typeof sourceInput === 'boolean') {
              if (sourceInput) { // true. part of the first event source
                  [eventSource] = hashValuesToArray(state.eventSources);
              }
          }
          else if (sourceInput != null) { // an ID. accepts a number too
              let sourceApi = this.getEventSourceById(sourceInput); // TODO: use an internal function
              if (!sourceApi) {
                  warn(`Unknown event source ID \`${sourceInput}\`.`); // TODO: test
                  return null;
              }
              eventSource = sourceApi.internalEventSource;
          }
          let tuple = parseEvent(eventInput, eventSource, state, false);
          if (tuple) {
              let newEventApi = new EventImpl(state, tuple.def, tuple.def.recurringDef ? null : tuple.instance);
              this.dispatch({
                  type: 'ADD_EVENTS',
                  eventStore: eventTupleToStore(tuple),
              });
              this.triggerEventAdd(newEventApi);
              return newEventApi;
          }
          return null;
      }
      triggerEventAdd(eventApi) {
          let { emitter } = this.getCurrentData();
          emitter.trigger('eventAdd', {
              event: eventApi,
              relatedEvents: [],
              revert: () => {
                  this.dispatch({
                      type: 'REMOVE_EVENTS',
                      eventStore: eventApiToStore(eventApi),
                  });
              },
          });
      }
      // TODO: optimize
      getEventById(id) {
          let state = this.getCurrentData();
          let { defs, instances } = state.eventStore;
          id = String(id);
          for (let defId in defs) {
              let def = defs[defId];
              if (def.publicId === id) {
                  if (def.recurringDef) {
                      return new EventImpl(state, def, null);
                  }
                  for (let instanceId in instances) {
                      let instance = instances[instanceId];
                      if (instance.defId === def.defId) {
                          return new EventImpl(state, def, instance);
                      }
                  }
              }
          }
          return null;
      }
      getEvents() {
          let currentData = this.getCurrentData();
          return buildEventApis(currentData.eventStore, currentData);
      }
      removeAllEvents() {
          this.dispatch({ type: 'REMOVE_ALL_EVENTS' });
      }
      // Public Event Sources API
      // -----------------------------------------------------------------------------------------------------------------
      getEventSources() {
          let state = this.getCurrentData();
          let sourceHash = state.eventSources;
          let sourceApis = [];
          for (let internalId in sourceHash) {
              sourceApis.push(new EventSourceImpl(state, sourceHash[internalId]));
          }
          return sourceApis;
      }
      getEventSourceById(id) {
          let state = this.getCurrentData();
          let sourceHash = state.eventSources;
          id = String(id);
          for (let sourceId in sourceHash) {
              if (sourceHash[sourceId].publicId === id) {
                  return new EventSourceImpl(state, sourceHash[sourceId]);
              }
          }
          return null;
      }
      addEventSource(sourceInput) {
          let state = this.getCurrentData();
          if (sourceInput instanceof EventSourceImpl) {
              // not already present? don't want to add an old snapshot
              if (!state.eventSources[sourceInput.internalEventSource.sourceId]) {
                  this.dispatch({
                      type: 'ADD_EVENT_SOURCES',
                      sources: [sourceInput.internalEventSource],
                  });
              }
              return sourceInput;
          }
          let eventSource = parseEventSource(sourceInput, state);
          if (eventSource) { // TODO: error otherwise?
              this.dispatch({ type: 'ADD_EVENT_SOURCES', sources: [eventSource] });
              return new EventSourceImpl(state, eventSource);
          }
          return null;
      }
      removeAllEventSources() {
          this.dispatch({ type: 'REMOVE_ALL_EVENT_SOURCES' });
      }
      refetchEvents() {
          this.dispatch({ type: 'FETCH_EVENT_SOURCES', isRefetch: true });
      }
      // Scroll
      // -----------------------------------------------------------------------------------------------------------------
      scrollToTime(timeInput) {
          let time = createDuration(timeInput);
          if (time) {
              this.trigger('_timeScrollRequest', time);
          }
      }
      // Button State
      // -----------------------------------------------------------------------------------------------------------------
      getButtonState() {
          const currentData = this.getCurrentData();
          const { toolbarProps } = currentData;
          const options = currentData.calendarOptions;
          const buttonConfigs = options.buttons || {};
          const viewSpecs = currentData.viewSpecs;
          const currentUnit = currentData.viewSpec.singleUnit;
          const currentHintOrdinal = [
              currentUnit ? getSingleUnitText(currentUnit, options) : '',
              currentUnit,
          ];
          const buttonState = {
              today: {
                  text: options.todayText,
                  hint: formatWithOrdinals(options.todayHint, currentHintOrdinal, options.todayText),
                  isDisabled: !toolbarProps.isTodayEnabled,
              },
              prev: {
                  text: options.prevText,
                  hint: formatWithOrdinals(options.prevHint, currentHintOrdinal, options.prevText),
                  isDisabled: !toolbarProps.isPrevEnabled,
              },
              next: {
                  text: options.nextText,
                  hint: formatWithOrdinals(options.nextHint, currentHintOrdinal, options.nextText),
                  isDisabled: !toolbarProps.isNextEnabled,
              },
              prevYear: {
                  text: options.prevYearText,
                  hint: formatWithOrdinals(options.prevHint, [options.yearText, 'year'], options.prevYearText),
                  isDisabled: false,
              },
              nextYear: {
                  text: options.prevYearText,
                  hint: formatWithOrdinals(options.nextHint, [options.yearText, 'year'], options.nextYearText),
                  isDisabled: false,
              },
          };
          for (const viewSpecName in viewSpecs) {
              const viewSpec = viewSpecs[viewSpecName];
              const { singleUnit } = viewSpec;
              const buttonTextKey = viewSpec.optionDefaults.buttonTextKey;
              const buttonText = buttonConfigs[viewSpecName]?.text ||
                  (buttonTextKey ? options[buttonTextKey] : '') ||
                  (singleUnit ? getSingleUnitText(singleUnit, options) : '') ||
                  viewSpecName;
              const buttonHint = formatWithOrdinals(options.viewHint, [buttonText, viewSpecName], // ordinal arguments
              buttonText);
              buttonState[viewSpecName] = {
                  text: buttonText,
                  hint: buttonHint,
              };
          }
          return buttonState;
      }
  }
  function getSingleUnitText(singleUnit, options) {
      return options[singleUnit + 'TextLong'] || options[singleUnit + 'Text'];
  }

  class CalendarMediaRoot extends C {
      constructor() {
          super(...arguments);
          this.state = {
              forPrint: false,
          };
          this.handleBeforePrint = () => {
              // The synchronous commit mounts print-only DOM during this beforeprint
              // task. Watchers registering during the bracket measure immediately, and
              // their layout recomputations settle in one batched drain before the
              // native event returns.
              flushSyncWithSizeBatching(() => {
                  this.setState({ forPrint: true });
              });
          };
          this.handleAfterPrint = () => {
              // No synchronous commit needed: nothing else listens to _afterprint, and
              // the ordinary microtask-batched re-render restores the screen DOM before
              // the next paint. Screen watchers keep their async-first measurement.
              this.setState({ forPrint: false });
          };
      }
      render() {
          return this.props?.children(this.state.forPrint);
      }
      componentDidMount() {
          const { props } = this;
          const { emitter } = props;
          emitter.on('_beforeprint', this.handleBeforePrint);
          emitter.on('_afterprint', this.handleAfterPrint);
      }
      componentWillUnmount() {
          const { props } = this;
          const { emitter } = props;
          emitter.off('_beforeprint', this.handleBeforePrint);
          emitter.off('_afterprint', this.handleAfterPrint);
      }
  }
  function computeRootClassName(options, forPrint) {
      let borderlessX = options.borderlessX ?? options.borderless;
      let borderlessTop = options.borderlessTop ?? options.borderless;
      let borderlessBottom = options.borderlessBottom ?? options.borderless;
      const calendarDisplayData = {
          borderlessX: Boolean(borderlessX),
          borderlessTop: Boolean(borderlessTop),
          borderlessBottom: Boolean(borderlessBottom),
      };
      return joinClassNames(generateClassName(options.class, calendarDisplayData), generateClassName(options.className, calendarDisplayData), classNames.borderBoxRoot, classNames.isolate, classNames.flexCol, forPrint ? classNames.calendarPrintRoot : classNames.calendarScreenRoot);
  }

  class ButtonIcon extends BaseComponent {
      render() {
          const { contentGenerator, className } = this.props;
          if (contentGenerator) {
              // TODO: somehow give className to the svg?
              return (u$1(ContentContainer, { tag: 'span', style: { display: 'contents' }, attrs: { 'aria-hidden': true }, renderProps: {}, generatorName: undefined, customGenerator: contentGenerator }));
          }
          if (className !== undefined) {
              return (u$1("span", { "aria-hidden": true, className: className }));
          }
      }
  }

  class ToolbarSection extends BaseComponent {
      render() {
          let { props } = this;
          let { options } = this.context;
          let children = props.widgetGroups.map((widgetGroup) => this.renderWidgetGroup(widgetGroup));
          return k$1('div', {
              className: generateClassName(options.toolbarSectionClass, { name: props.name }),
          }, ...children);
      }
      renderWidgetGroup(widgetGroup) {
          let { props, context } = this;
          let { options } = context;
          let children = [];
          let isOnlyButtons = true;
          let isOnlyView = true;
          for (const widget of widgetGroup) {
              const { name, isView } = widget;
              if (name === 'title') {
                  isOnlyButtons = false;
              }
              else if (!isView) {
                  isOnlyView = false;
              }
          }
          for (let widget of widgetGroup) {
              let { name, customElement, buttonHint } = widget;
              if (name === 'title') {
                  children.push(u$1("div", { role: 'heading', "aria-level": options.headingLevel, id: props.titleId, className: joinClassNames(options.toolbarTitleClass), children: props.title }));
              }
              else if (customElement) {
                  children.push(u$1(ContentContainer, { tag: 'span', style: { display: 'contents' }, renderProps: {}, generatorName: undefined, customGenerator: customElement }));
              }
              else {
                  let isSelected = name === props.selectedButton;
                  let isDisabled = (!props.isTodayEnabled && name === 'today') ||
                      (!props.isPrevEnabled && name === 'prev') ||
                      (!props.isNextEnabled && name === 'next');
                  let buttonDisplay = widget.buttonDisplay ?? options.buttonDisplay;
                  if (buttonDisplay === 'auto') {
                      buttonDisplay = (widget.buttonIconContent || widget.buttonIconClass)
                          ? 'icon'
                          : 'text';
                  }
                  let iconNode;
                  if (buttonDisplay !== 'text') {
                      iconNode = (u$1(ButtonIcon, { className: widget.buttonIconClass, contentGenerator: widget.buttonIconContent }));
                  }
                  let inGroup = widgetGroup.length > 1 && isOnlyButtons;
                  let buttonGroup = inGroup ? { hasSelection: isOnlyView } : null;
                  let renderProps = {
                      name,
                      text: widget.buttonText,
                      isPrimary: widget.buttonIsPrimary,
                      isSelected,
                      isDisabled,
                      isIconOnly: buttonDisplay === 'icon',
                      buttonGroup,
                  };
                  children.push(u$1(ContentContainer, { tag: 'button', attrs: {
                          type: 'button',
                          disabled: isDisabled,
                          ...((isOnlyButtons && isOnlyView)
                              ? { 'role': 'tab', 'aria-selected': isSelected }
                              : { 'aria-pressed': isSelected }),
                          'aria-label': typeof buttonHint === 'function'
                              ? buttonHint(props.navUnit)
                              : buttonHint,
                          onClick: widget.buttonClick,
                      }, className: joinClassNames(generateClassName(options.buttonClass, renderProps), !isDisabled && classNames.cursorPointer, inGroup && joinClassNames(isSelected ? classNames.z1 : classNames.z0, classNames.focusZ2)), renderProps: renderProps, generatorName: undefined, classNameGenerator: widget.buttonClass, didMount: widget.buttonDidMount, willUnmount: widget.buttonWillUnmount, children: () => (buttonDisplay === 'text'
                          ? widget.buttonText
                          : buttonDisplay === 'icon'
                              ? iconNode
                              : buttonDisplay === 'icon-text'
                                  ? (u$1(S, { children: [iconNode, widget.buttonText] }))
                                  : (u$1(S, { children: [widget.buttonText, iconNode] })) // text-icon
                      ) }));
              }
          }
          if (children.length > 1) {
              return k$1('div', {
                  role: (isOnlyButtons && isOnlyView) ? 'tablist' : undefined,
                  'aria-label': (isOnlyButtons && isOnlyView) ? options.viewChangeHint : undefined,
                  className: joinClassNames(generateClassName(options.buttonGroupClass, { hasSelection: isOnlyView }), classNames.isolate),
              }, ...children);
          }
          return children[0];
      }
  }

  class Toolbar extends BaseComponent {
      render() {
          let { props } = this;
          let options = this.context.options;
          let { sectionWidgets } = props.model;
          const { borderlessX, borderlessTop, borderlessBottom } = computeViewBorderless(options);
          const toolbarClassOption = props.isHeader ? options.headerToolbarClass : options.footerToolbarClass;
          return (u$1("div", { className: joinClassNames(generateClassName(toolbarClassOption, { borderlessX, borderlessTop, borderlessBottom }), generateClassName(options.toolbarClass, { borderlessX, borderlessTop, borderlessBottom })), children: [this.renderSection('start', sectionWidgets.start), this.renderSection('center', sectionWidgets.center), this.renderSection('end', sectionWidgets.end)] }));
      }
      renderSection(name, widgetGroups) {
          let { props } = this;
          return (u$1(ToolbarSection, { name: name, widgetGroups: widgetGroups, title: props.title, titleId: props.titleId, navUnit: props.navUnit, selectedButton: props.selectedButton, isTodayEnabled: props.isTodayEnabled, isPrevEnabled: props.isPrevEnabled, isNextEnabled: props.isNextEnabled }, name));
      }
  }

  /*
  Detects when the user clicks on an event within a DateComponent
  */
  class EventClicking extends Interaction {
      constructor(settings) {
          super(settings);
          this.handleSegClick = (ev, segEl) => {
              let { component } = this;
              let { context } = component;
              let eventRange = getElEventRange(segEl);
              if (eventRange && // might be the <div> surrounding the more link
                  component.isValidSegDownEl(ev.target)) {
                  context.emitter.trigger('eventClick', {
                      el: segEl,
                      event: new EventImpl(component.context, eventRange.def, eventRange.instance),
                      jsEvent: ev, // Is this always a mouse event? See #4655
                      view: context.viewApi,
                  });
              }
          };
          this.destroy = listenBySelector(settings.el, 'click', `.${classNames.internalEvent}`, // on both fg and bg events
          this.handleSegClick);
      }
  }

  /*
  Triggers events and adds/removes core classNames when the user's pointer
  enters/leaves event-elements of a component.
  */
  class EventHovering extends Interaction {
      constructor(settings) {
          super(settings);
          // for simulating an eventMouseLeave when the event el is destroyed while mouse is over it
          this.handleEventElRemove = (el) => {
              if (el === this.currentSegEl) {
                  this.handleSegLeave(null, this.currentSegEl);
              }
          };
          this.handleSegEnter = (ev, segEl) => {
              if (getElEventRange(segEl)) { // TODO: better way to make sure not hovering over more+ link or its wrapper
                  this.currentSegEl = segEl;
                  this.triggerEvent('eventMouseEnter', ev, segEl);
              }
          };
          this.handleSegLeave = (ev, segEl) => {
              if (this.currentSegEl) {
                  this.currentSegEl = null;
                  this.triggerEvent('eventMouseLeave', ev, segEl);
              }
          };
          this.removeHoverListeners = listenToHoverBySelector(settings.el, `.${classNames.internalEvent}`, // on both fg and bg events
          this.handleSegEnter, this.handleSegLeave);
      }
      destroy() {
          this.removeHoverListeners();
      }
      triggerEvent(publicEvName, ev, segEl) {
          let { component } = this;
          let { context } = component;
          let eventRange = getElEventRange(segEl);
          if (!ev || component.isValidSegDownEl(ev.target)) {
              context.emitter.trigger(publicEvName, {
                  el: segEl,
                  event: new EventImpl(context, eventRange.def, eventRange.instance),
                  jsEvent: ev, // Is this always a mouse event? See #4655
                  view: context.viewApi,
              });
          }
      }
  }

  class CalendarInner extends PureComponent {
      constructor() {
          super(...arguments);
          this.buildViewContext = memoize(buildViewContext);
          this.buildViewPropTransformers = memoize(buildViewPropTransformers);
          this.interactionsStore = {};
          this.calendarInteractions = [];
          this.registerInteractiveComponent = (component, settingsInput) => {
              let settings = parseInteractionSettings(component, settingsInput);
              let DEFAULT_INTERACTIONS = [
                  EventClicking,
                  EventHovering,
              ];
              let interactionClasses = DEFAULT_INTERACTIONS;
              if (!settingsInput.disableHits) {
                  interactionClasses = interactionClasses.concat(this.props.pluginHooks.componentInteractions);
              }
              let interactions = interactionClasses.map((TheInteractionClass) => new TheInteractionClass(settings));
              this.interactionsStore[component.uid] = interactions;
              interactionSettingsStore[component.uid] = settings;
          };
          this.unregisterInteractiveComponent = (component) => {
              let listeners = this.interactionsStore[component.uid];
              if (listeners) {
                  for (let listener of listeners) {
                      listener.destroy();
                  }
                  delete this.interactionsStore[component.uid];
              }
              delete interactionSettingsStore[component.uid];
          };
      }
      get viewTitleId() {
          return this.props.baseId + 'title';
      }
      render() {
          const { props } = this;
          let { toolbarConfig, options } = props;
          let viewHeight;
          let viewHeightLiquid = false;
          let viewAspectRatio;
          if (props.forPrint || getIsHeightAuto(options)) ;
          else if (options.height != null) {
              viewHeightLiquid = true;
          }
          else if (options.contentHeight != null) {
              viewHeight = options.contentHeight;
          }
          else {
              viewAspectRatio = Math.max(options.aspectRatio, 0.5); // prevent from getting too tall
          }
          let viewContext = this.buildViewContext(props.viewSpec, props.viewApi, props.options, props.dateProfileGenerator, props.dateEnv, props.nowManager, props.pluginHooks, props.dispatch, props.getCurrentData, props.emitter, props.calendarApi, props.baseId, this.registerInteractiveComponent, this.unregisterInteractiveComponent);
          return (u$1(ViewContextType.Provider, { value: viewContext, children: [toolbarConfig.header && (u$1(Toolbar, { model: toolbarConfig.header, isHeader: true, titleId: this.viewTitleId, ...props.toolbarProps })), u$1("div", { className: joinClassNames(classNames.flexCol, classNames.rel, 
                      // prevents browsers' "scroll anchoring behavior", which cause scroll thrashing
                      // when clicking "Next" for month-view, because rows would flex-grow while other rows
                      // temporarily removed. This behavior probably universally unhelpful for our uses,
                      // esp with virtualization, but maybe in future put on more specific row-based parents
                      classNames.overflowAnchorNone, 
                      // workaround for Safari pushing content area extremely wide after returning from
                      // print-view. probably a good idea regardless, to circumvent 'auto' dimentions
                      classNames.minHeight0, viewHeightLiquid && classNames.liquid), style: {
                          height: viewHeight,
                          aspectRatio: viewAspectRatio != null ? String(viewAspectRatio) : undefined,
                      }, children: [this.renderView(joinClassNames((viewHeightLiquid || viewHeight) && classNames.liquid, viewAspectRatio != null && classNames.fill, classNames.internalView)), this.buildAppendContent()] }), toolbarConfig.footer && (u$1(Toolbar, { model: toolbarConfig.footer, isHeader: false, ...props.toolbarProps }))] }));
      }
      renderView(className) {
          const { props } = this;
          const { pluginHooks, viewSpec, toolbarConfig, toolbarProps } = props;
          let viewProps = {
              className,
              dateProfile: props.dateProfile,
              businessHours: props.businessHours,
              eventStore: props.renderableEventStore, // !
              eventUiBases: props.eventUiBases,
              dateSelection: props.dateSelection,
              eventSelection: props.eventSelection,
              eventDrag: props.eventDrag,
              eventResize: props.eventResize,
              forPrint: props.forPrint,
              labelId: toolbarConfig.header && toolbarConfig.header.hasTitle ? this.viewTitleId : undefined,
              labelStr: toolbarConfig.header && toolbarConfig.header.hasTitle ? undefined : toolbarProps.title,
          };
          let transformers = this.buildViewPropTransformers(pluginHooks.viewPropsTransformers);
          let contentProps = {
              ...props,
              toolbarProps,
              forPrint: props.forPrint,
          };
          for (let transformer of transformers) {
              Object.assign(viewProps, transformer.transform(viewProps, contentProps));
          }
          let ViewComponent = viewSpec.component;
          return (u$1(ViewComponent, { ...viewProps }));
      }
      buildAppendContent() {
          const { props } = this;
          return (u$1(S, { children: props.pluginHooks.viewContainerAppends.map((buildAppendContent, i) => (u$1(S, { children: buildAppendContent(props) }, i))) }));
      }
      // BE AWARE React StrictMode might execute this twice
      componentDidMount() {
          const { props } = this;
          this.calendarInteractions = props.pluginHooks.calendarInteractions
              .map((CalendarInteractionClass) => new CalendarInteractionClass(props));
          let { propSetHandlers } = props.pluginHooks;
          for (let propName in propSetHandlers) {
              propSetHandlers[propName](props[propName], props);
          }
          // call contextInit
          for (let callback of props.pluginHooks.contextInit) {
              callback(props);
          }
      }
      componentDidUpdate(prevProps) {
          const { props } = this;
          let { propSetHandlers } = props.pluginHooks;
          for (let propName in propSetHandlers) {
              if (props[propName] !== prevProps[propName]) {
                  propSetHandlers[propName](props[propName], props);
              }
          }
      }
      // BE AWARE React StrictMode might execute this twice
      componentWillUnmount() {
          const { props } = this;
          for (let interaction of this.calendarInteractions) {
              interaction.destroy();
          }
          this.calendarInteractions = [];
          // will likely undo what was done by contextInit
          props.emitter.trigger('_unmount');
      }
  }
  function buildViewPropTransformers(theClasses) {
      return theClasses.map((TheClass) => new TheClass());
  }

  function pointInsideRect(point, rect) {
      return point.left >= rect.left &&
          point.left < rect.right &&
          point.top >= rect.top &&
          point.top < rect.bottom;
  }
  // Returns a new rectangle that is the intersection of the two rectangles. If they don't intersect, returns false
  function intersectRects(rect1, rect2) {
      let res = {
          left: Math.max(rect1.left, rect2.left),
          right: Math.min(rect1.right, rect2.right),
          top: Math.max(rect1.top, rect2.top),
          bottom: Math.min(rect1.bottom, rect2.bottom),
      };
      if (res.left < res.right && res.top < res.bottom) {
          return res;
      }
      return false;
  }
  // Returns a new point that will have been moved to reside within the given rectangle
  function constrainPoint(point, rect) {
      return {
          left: Math.min(Math.max(point.left, rect.left), rect.right),
          top: Math.min(Math.max(point.top, rect.top), rect.bottom),
      };
  }
  // Returns a point that is the center of the given rectangle
  function getRectCenter(rect) {
      return {
          left: (rect.left + rect.right) / 2,
          top: (rect.top + rect.bottom) / 2,
      };
  }
  // Subtracts point2's coordinates from point1's coordinates, returning a delta
  function diffPoints(point1, point2) {
      return {
          left: point1.left - point2.left,
          top: point1.top - point2.top,
      };
  }

  function computeEdges(el, getPadding = false) {
      let computedStyle = window.getComputedStyle(el);
      let borderLeft = parseInt(computedStyle.borderLeftWidth, 10) || 0;
      let borderRight = parseInt(computedStyle.borderRightWidth, 10) || 0;
      let borderTop = parseInt(computedStyle.borderTopWidth, 10) || 0;
      let borderBottom = parseInt(computedStyle.borderBottomWidth, 10) || 0;
      let badScrollbarWidths = computeScrollbarWidthsForEl(el); // includes border!
      let scrollbarLeftRight = badScrollbarWidths.y - borderLeft - borderRight;
      let scrollbarBottom = badScrollbarWidths.x - borderTop - borderBottom;
      let res = {
          borderLeft,
          borderRight,
          borderTop,
          borderBottom,
          scrollbarBottom,
          scrollbarLeft: 0,
          scrollbarRight: 0,
      };
      if (computedStyle.direction === 'rtl') {
          res.scrollbarLeft = scrollbarLeftRight;
      }
      else {
          res.scrollbarRight = scrollbarLeftRight;
      }
      if (getPadding) {
          res.paddingLeft = parseInt(computedStyle.paddingLeft, 10) || 0;
          res.paddingRight = parseInt(computedStyle.paddingRight, 10) || 0;
          res.paddingTop = parseInt(computedStyle.paddingTop, 10) || 0;
          res.paddingBottom = parseInt(computedStyle.paddingBottom, 10) || 0;
      }
      return res;
  }
  function computeInnerRect(el, goWithinPadding = false, doFromWindowViewport) {
      let outerRect = doFromWindowViewport ? el.getBoundingClientRect() : computeRect(el);
      let edges = computeEdges(el, goWithinPadding);
      let res = {
          left: outerRect.left + edges.borderLeft + edges.scrollbarLeft,
          right: outerRect.right - edges.borderRight - edges.scrollbarRight,
          top: outerRect.top + edges.borderTop,
          bottom: outerRect.bottom - edges.borderBottom - edges.scrollbarBottom,
      };
      if (goWithinPadding) {
          res.left += edges.paddingLeft;
          res.right -= edges.paddingRight;
          res.top += edges.paddingTop;
          res.bottom -= edges.paddingBottom;
      }
      return res;
  }
  function computeRect(el) {
      let rect = el.getBoundingClientRect();
      return {
          left: rect.left + window.scrollX,
          top: rect.top + window.scrollY,
          right: rect.right + window.scrollX,
          bottom: rect.bottom + window.scrollY,
      };
  }
  /*
  Returns relative to viewport origin
  */
  function computeClippedClientRect(el) {
      let clippingParents = getClippingParents(el);
      let rect = el.getBoundingClientRect();
      for (let clippingParent of clippingParents) {
          let intersection = intersectRects(rect, clippingParent.getBoundingClientRect());
          if (intersection) {
              rect = intersection;
          }
          else {
              return null;
          }
      }
      return rect;
  }
  // does not return window
  function getClippingParents(el) {
      let parents = [];
      while (el instanceof HTMLElement) { // will stop when gets to document or null
          let computedStyle = window.getComputedStyle(el);
          if (computedStyle.position === 'fixed') {
              break;
          }
          if ((/(auto|scroll)/).test(computedStyle.overflow + computedStyle.overflowY + computedStyle.overflowX)) {
              parents.push(el);
          }
          el = el.parentNode;
      }
      return parents;
  }
  // WARNING: will include border
  function computeScrollbarWidthsForEl(el) {
      return {
          x: el.offsetHeight - el.clientHeight,
          y: el.offsetWidth - el.clientWidth,
      };
  }

  function getAppendableRoot(el) {
      const root = el.getRootNode();
      if (root instanceof Document) {
          return root.body || root.documentElement; // pick body if available
      }
      return root;
  }
  function computeElIsRtl(el) {
      return getComputedStyle(el).direction === 'rtl';
  }
  // Style
  // ----------------------------------------------------------------------------------------------------------------
  const PIXEL_PROP_RE = /(top|left|right|bottom|width|height)$/i;
  function applyStyle(el, props) {
      for (let propName in props) {
          applyStyleProp(el, propName, props[propName]);
      }
  }
  function applyStyleProp(el, name, val) {
      if (val == null) {
          el.style[name] = '';
      }
      else if (typeof val === 'number' && PIXEL_PROP_RE.test(name)) {
          el.style[name] = `${val}px`;
      }
      else {
          el.style[name] = val;
      }
  }
  // Event Handling
  // ----------------------------------------------------------------------------------------------------------------
  // if intercepting bubbled events at the document/window/body level,
  // and want to see originating element (the 'target'), use this util instead
  // of `ev.target` because it goes within web-component boundaries.
  function getEventTargetViaRoot(ev) {
      return ev.composedPath?.()[0] ?? ev.target;
  }

  class NowTimer extends C {
      constructor(props, context) {
          super(props, context);
          this.handleChange = () => {
              this.forceUpdate();
          };
          this.runner = new NowTimerRunner(this.handleChange);
      }
      render() {
          const { props, context } = this;
          const { nowDate, nowMs, todayRange } = this.runner.update({
              nowManager: context.nowManager,
              unit: props.unit,
              unitValue: props.unitValue,
              nowIndicatorSnap: context.options.nowIndicatorSnap,
              dateEnv: context.dateEnv,
          });
          return props.children(nowDate, todayRange, nowMs);
      }
      componentWillUnmount() {
          this.runner.destroy();
      }
  }
  NowTimer.contextType = ViewContextType;

  const FULL_DATE_FORMAT = createFormatter({ year: 'numeric', month: 'long', day: 'numeric' });
  const WEEK_FORMAT = createFormatter({ week: 'long' });
  const WEEKDAY_ONLY_FORMAT = createFormatter({
      weekday: 'long',
  });
  function findWeekdayText(parts) {
      for (const part of parts) {
          if (part.type === 'weekday') {
              return part.value;
          }
      }
      return '';
  }
  function findDayNumberText(parts) {
      for (const part of parts) {
          if (part.type === 'day') {
              return part.value;
          }
      }
      return '';
  }
  function findMonthText(parts) {
      for (const part of parts) {
          if (part.type === 'month') {
              return part.value;
          }
      }
      return '';
  }

  /*
  TODO: just have this return the string?
  */
  function buildDateStr(context, dateMarker, viewType = 'day') {
      return joinDateTimeFormatParts(context.dateEnv.formatToParts(dateMarker, viewType === 'week' ? WEEK_FORMAT : FULL_DATE_FORMAT));
  }
  /*
  Assumes navLinks enabled
  Always hidden to screen readers. Do not point aria-labelledby at this. Use aria-label instead.
  */
  function buildNavLinkAttrs(context, dateMarker, viewType = 'day', dateStr = buildDateStr(context, dateMarker, viewType), isTabbable = true) {
      const { dateEnv, options, calendarApi } = context;
      const zonedDate = dateEnv.toDate(dateMarker);
      const handleInteraction = (ev) => {
          let customAction = viewType === 'day' ? options.navLinkDayClick :
              viewType === 'week' ? options.navLinkWeekClick : null;
          if (typeof customAction === 'function') {
              customAction.call(calendarApi, dateEnv.toDate(dateMarker), ev);
          }
          else {
              if (typeof customAction === 'string') {
                  viewType = customAction;
              }
              calendarApi.zoomTo(dateMarker, viewType);
          }
      };
      return {
          'role': 'link', // TODO
          'aria-label': formatWithOrdinals(options.navLinkHint, [dateStr, zonedDate], dateStr),
          'className': joinClassNames(options.navLinkClass, classNames.cursorPointer, classNames.internalNavLink),
          ...(isTabbable
              ? createAriaClickAttrs(handleInteraction)
              : { onClick: handleInteraction }),
      };
  }

  function getDateMeta(dateMarker, dateEnv, dateProfile, todayRange, nowDate) {
      const isDisabled = Boolean(dateProfile && (!dateProfile.activeRange || !rangeContainsMarker(dateProfile.activeRange, dateMarker)));
      return {
          date: dateEnv.toDate(dateMarker),
          dow: dateMarker.getUTCDay(),
          isDisabled,
          isOther: !isDisabled && Boolean(dateProfile && !rangeContainsMarker(dateProfile.currentRange, dateMarker)),
          isToday: !isDisabled && Boolean(todayRange && rangeContainsMarker(todayRange, dateMarker)),
          isPast: !isDisabled && Boolean(nowDate ? (dateMarker < nowDate) : todayRange ? (dateMarker < todayRange.start) : false),
          isFuture: !isDisabled && Boolean(nowDate ? (dateMarker > nowDate) : todayRange ? (dateMarker >= todayRange.end) : false),
      };
  }

  class ViewContainer extends BaseComponent {
      constructor() {
          super(...arguments);
          this.refineRenderProps = memoizeObjArg(refineRenderProps$1);
      }
      render() {
          const { props, context } = this;
          const { options, viewSpec } = context;
          const renderProps = this.refineRenderProps({
              ...computeViewBorderless(options),
              options: { headerToolbar: options.headerToolbar, footerToolbar: options.footerToolbar },
              isHeightAuto: getIsHeightAuto(options),
              viewApi: context.viewApi,
          });
          return (u$1(ContentContainer, { elRef: props.elRef, tag: props.tag || 'div', attrs: props.attrs, style: props.style, className: joinClassNames(props.className, generateClassName(options.viewClass, renderProps), 
              // WORKAROUND for way calendar's className would get merged into view's className
              generateClassName(viewSpec.optionDefaults.class, renderProps), generateClassName(viewSpec.optionDefaults.className, renderProps), generateClassName(viewSpec.optionOverrides.class, renderProps), generateClassName(viewSpec.optionOverrides.className, renderProps)), renderProps: renderProps, generatorName: undefined, didMount: options.didMount || options.viewDidMount, willUnmount: options.willUnmount || options.viewWillUnmount, children: () => props.children }));
      }
  }
  function refineRenderProps$1(raw) {
      return {
          view: raw.viewApi,
          borderlessX: raw.borderlessX,
          borderlessTop: raw.borderlessTop,
          borderlessBottom: raw.borderlessBottom,
          options: raw.options,
          isHeightAuto: raw.isHeightAuto,
      };
  }

  /*
  an INTERACTABLE date component

  PURPOSES:
  - hook up to fg, fill, and mirror renderers
  - interface for dragging and hits
  */
  class DateComponent extends BaseComponent {
      constructor() {
          super(...arguments);
          this.uid = guid();
      }
      // Hit System
      // -----------------------------------------------------------------------------------------------------------------
      prepareHits() {
      }
      queryHit(isRtl, positionLeft, positionTop, elWidth, elHeight) {
          return null; // this should be abstract
      }
      // Pointer Interaction Utils
      // -----------------------------------------------------------------------------------------------------------------
      isValidSegDownEl(el) {
          return !this.props.eventDrag && // HACK
              !this.props.eventResize && // HACK
              !el.closest(`.${classNames.internalEventMirror}`);
      }
      isValidDateDownEl(el) {
          return !el.closest(`.${classNames.internalEvent}:not(.${classNames.internalBgEvent})`) &&
              !el.closest(`.${classNames.internalMoreLink}`) &&
              !el.closest(`.${classNames.internalNavLink}`) &&
              !el.closest(`.${classNames.internalPopover}`); // hack
      }
  }

  class DelayedRunner {
      constructor(drainedOption) {
          this.drainedOption = drainedOption;
          this.isRunning = false;
          this.isDirty = false;
          this.pauseDepths = {};
          this.timeoutId = 0;
      }
      request(delay) {
          this.isDirty = true;
          if (!this.isPaused()) {
              this.clearTimeout();
              if (delay == null) {
                  this.tryDrain();
              }
              else {
                  this.timeoutId = setTimeout(// NOT OPTIMAL! TODO: look at debounce
                  this.tryDrain.bind(this), delay);
              }
          }
      }
      pause(scope = '') {
          let { pauseDepths } = this;
          pauseDepths[scope] = (pauseDepths[scope] || 0) + 1;
          this.clearTimeout();
      }
      resume(scope = '', force) {
          let { pauseDepths } = this;
          if (scope in pauseDepths) {
              if (force) {
                  delete pauseDepths[scope];
              }
              else {
                  pauseDepths[scope] -= 1;
                  let depth = pauseDepths[scope];
                  if (depth <= 0) {
                      delete pauseDepths[scope];
                  }
              }
              this.tryDrain();
          }
      }
      isPaused() {
          return Object.keys(this.pauseDepths).length;
      }
      tryDrain() {
          if (!this.isRunning && !this.isPaused()) {
              this.isRunning = true;
              while (this.isDirty) {
                  this.isDirty = false;
                  this.drained(); // might set isDirty to true again
              }
              this.isRunning = false;
          }
      }
      clear() {
          this.clearTimeout();
          this.isDirty = false;
          this.pauseDepths = {};
      }
      clearTimeout() {
          if (this.timeoutId) {
              clearTimeout(this.timeoutId);
              this.timeoutId = 0;
          }
      }
      drained() {
          if (this.drainedOption) {
              this.drainedOption();
          }
      }
  }

  /*
  NOTE: detection is complicated (w/ touch and wheel) because ScrollerSyncer needs to know about it,
  but are we sure we can't just ignore programmatic scrollTo() calls with a flag? and determine the
  the scroll-master simply by who was the newest scroller? Does passive:true do things asynchronously?
  */
  class ScrollListener {
      constructor(el) {
          this.el = el;
          this.emitter = new Emitter();
          this.isScroll = false;
          this.isScrollRecent = false;
          this.isWheelRecent = false;
          this.isMouseDown = false; // user currently has mouse down?
          this.isTouchDown = false; // user currently has finger down?
          // accumulated during scroll
          this.isMouse = false;
          this.isTouch = false;
          this.isWheel = false;
          // Handlers
          // ----------------------------------------------------------------------------------------------
          this.handleScroll = () => {
              this.isScrollRecent = true;
              if (this.isMouseDown) {
                  this.isMouse = true;
              }
              if (this.isTouchDown) {
                  this.isTouch = true;
              }
              if (this.isWheelRecent) {
                  this.isWheel = true;
              }
              this.startScroll();
              this.emitter.trigger('scroll', this.getIsDevice());
              this.scrollWaiter.request(500);
          };
          this.handleScrollWait = () => {
              this.isScrollRecent = false;
              // only end the scroll if not currently touching.
              // if touching, the scrolling will end later, on touchend.
              if (!this.isTouchDown) {
                  this.endScroll();
              }
          };
          // will fire *before* the scroll event is fired (might not cause a scroll!)
          this.handleWheel = () => {
              this.isWheelRecent = true;
              this.wheelWaiter.request(500);
          };
          this.handleWheelWait = () => {
              this.isWheelRecent = false;
          };
          this.handleMouseDown = () => {
              this.isMouseDown = true;
          };
          this.handleMouseUp = () => {
              this.isMouseDown = false;
          };
          // will fire *before* the scroll event is fired (might not cause a scroll!)
          this.handleTouchStart = () => {
              this.isTouchDown = true;
          };
          this.handleTouchEnd = () => {
              this.isTouchDown = false;
              // if the user ended their touch, and the scroll area wasn't moving,
              // we consider this to be the end of the scroll
              // otherwise, wait for inertia to finish and handleScrollWait to fire
              if (!this.isScrollRecent) {
                  this.endScroll();
              }
          };
          this.wheelWaiter = new DelayedRunner(this.handleWheelWait);
          this.scrollWaiter = new DelayedRunner(this.handleScrollWait);
          el.addEventListener('scroll', this.handleScroll, { passive: true });
          el.addEventListener('wheel', this.handleWheel, { passive: true });
          el.addEventListener('mousedown', this.handleMouseDown);
          el.addEventListener('mouseup', this.handleMouseUp);
          el.addEventListener('touchstart', this.handleTouchStart, { passive: true });
          el.addEventListener('touchend', this.handleTouchEnd);
      }
      destroy() {
          let { el } = this;
          el.removeEventListener('scroll', this.handleScroll, { passive: true });
          el.removeEventListener('wheel', this.handleWheel, { passive: true });
          el.removeEventListener('mousedown', this.handleMouseDown);
          el.removeEventListener('mouseup', this.handleMouseUp);
          el.removeEventListener('touchstart', this.handleTouchStart, { passive: true });
          el.removeEventListener('touchend', this.handleTouchEnd);
      }
      // Start / Stop
      // ----------------------------------------------------------------------------------------------
      startScroll() {
          if (!this.isScroll) {
              this.isScroll = true;
              this.emitter.trigger('scrollStart', this.getIsDevice());
          }
      }
      endScroll() {
          if (this.isScroll) { // extra protection because might be called publicly
              this.scrollWaiter.clear(); // (same)
              this.wheelWaiter.clear(); // (same)
              this.isScroll = false;
              this.isWheelRecent = false;
              this.emitter.trigger('scrollEnd', this.getIsDevice());
              this.isMouse = false;
              this.isTouch = false;
              this.isWheel = false;
          }
      }
      getIsDevice() {
          return this.isWheel || this.isMouse || this.isTouch;
      }
  }

  class Scroller extends DateComponent {
      constructor() {
          super(...arguments);
          this.handleEl = (el) => {
              if (this.el) {
                  this.el = null;
                  this._isUnmounting = true;
                  this.listener.destroy();
              }
              if (el) {
                  this.el = el;
                  this._isUnmounting = false;
                  this.listener = new ScrollListener(el);
              }
          };
          this.handleHRuler = (el) => {
              if (this.disconnectHRuler) {
                  this.disconnectHRuler();
                  this.disconnectHRuler = undefined;
                  if (this.clientWidth !== undefined) {
                      this.clientWidth = undefined;
                      setRef(this.props.clientWidthRef, null);
                  }
              }
              if (el) {
                  this.disconnectHRuler = watchWidth(el, (clientWidth) => {
                      if (this._isUnmounting)
                          return;
                      if (clientWidth !== this.clientWidth) {
                          this.clientWidth = clientWidth;
                          setRef(this.props.clientWidthRef, clientWidth);
                      }
                  });
              }
          };
          this.handleVRuler = (el) => {
              if (this.disconnectVRuler) {
                  this.disconnectVRuler();
                  this.disconnectVRuler = undefined;
                  if (this.clientHeight !== undefined) {
                      this.clientHeight = undefined;
                      setRef(this.props.clientHeightRef, null);
                  }
              }
              if (el) {
                  this.disconnectVRuler = watchHeight(el, (clientHeight) => {
                      if (this._isUnmounting)
                          return;
                      if (clientHeight !== this.clientHeight) {
                          this.clientHeight = clientHeight;
                          setRef(this.props.clientHeightRef, clientHeight);
                      }
                      const bottomScrollbarWidth = Math.round(this.el.getBoundingClientRect().height - clientHeight);
                      if (bottomScrollbarWidth !== this.bottomScrollbarWidth) {
                          this.bottomScrollbarWidth = bottomScrollbarWidth;
                          setRef(this.props.bottomScrollbarWidthRef, bottomScrollbarWidth);
                      }
                  });
              }
          };
      }
      render() {
          const { props } = this;
          // if there's only one axis that needs scrolling, the other axis will unintentionally have
          // scrollbars too if we don't force to 'hidden'
          const fallbackOverflow = (props.horizontal || props.vertical) ? 'hidden' : '';
          return (u$1("div", { ref: this.handleEl, className: joinClassNames(props.className, classNames.noPadding, classNames.rel, // for children fillTop/fillStart
              props.hideScrollbars && classNames.noScrollbars, classNames.internalScroller), style: {
                  ...props.style,
                  overflowX: (props.horizontal ? 'auto' : fallbackOverflow),
                  overflowY: (props.vertical ? 'auto' : fallbackOverflow),
              }, children: [props.children, Boolean(props.clientWidthRef) && (u$1("div", { ref: this.handleHRuler, className: classNames.fillTop })), Boolean(props.clientHeightRef || props.bottomScrollbarWidthRef) && (u$1("div", { ref: this.handleVRuler, className: classNames.fillStart }))] }));
      }
      endScroll() {
          this.listener.endScroll();
      }
      // Public API
      // -----------------------------------------------------------------------------------------------
      get x() {
          const { el } = this;
          return el ? getNormalizedScrollX(el) : 0;
      }
      get y() {
          const { el } = this;
          return el ? el.scrollTop : 0;
      }
      scrollTo({ x, y }) {
          const { el } = this;
          if (el) {
              if (y != null) {
                  el.scrollTop = y;
              }
              if (x != null) {
                  setNormalizedScrollX(el, x);
              }
          }
      }
      addScrollStartListener(handler) {
          this.listener.emitter.on('scrollStart', handler);
      }
      removeScrollStartListener(handler) {
          this.listener.emitter.off('scrollStart', handler);
      }
      addScrollEndListener(handler) {
          this.listener.emitter.on('scrollEnd', handler);
      }
      removeScrollEndListener(handler) {
          this.listener.emitter.off('scrollEnd', handler);
      }
  }
  // Public API
  // -------------------------------------------------------------------------------------------------
  // We can drop normalization when support for Chromium-based <86 is dropped (see Notion)
  function getNormalizedScrollX(el) {
      const { scrollLeft } = el;
      const isRtl = computeElIsRtl(el);
      return isRtl ? getNormalizedRtlScrollX(scrollLeft, el) : scrollLeft;
  }
  function setNormalizedScrollX(el, x) {
      const isRtl = computeElIsRtl(el);
      el.scrollLeft = isRtl ? getNormalizedRtlScrollLeft(x, el) : x;
  }
  /*
  Returns a value in the 'reverse' system
  */
  function getNormalizedRtlScrollX(scrollLeft, el) {
      switch (getRtlScrollerSystem()) {
          case 'positive':
              return el.scrollWidth - el.clientWidth - scrollLeft;
          case 'negative':
              return -scrollLeft;
      }
      return scrollLeft;
  }
  /*
  Receives a value in the 'reverse' system
  TODO: is this really the same equations as getNormalizedRtlScrollX??? I think so
    If so, consolidate. With isRtl check too
  */
  function getNormalizedRtlScrollLeft(x, el) {
      switch (getRtlScrollerSystem()) {
          case 'positive':
              return el.scrollWidth - el.clientWidth - x;
          case 'negative':
              return -x;
      }
      return x;
  }
  let _rtlScrollerSystem;
  function getRtlScrollerSystem() {
      return _rtlScrollerSystem || (_rtlScrollerSystem = detectRtlScrollerSystem());
  }
  function detectRtlScrollerSystem() {
      let el = document.createElement('div');
      el.style.position = 'absolute';
      el.style.top = '-1000px';
      el.style.width = '100px'; // must be at least the side of scrollbars or you get inaccurate values (#7335)
      el.style.height = '100px'; // "
      el.style.overflow = 'scroll';
      el.style.direction = 'rtl';
      let innerEl = document.createElement('div');
      innerEl.style.width = '200px';
      innerEl.style.height = '200px';
      el.appendChild(innerEl);
      document.body.appendChild(el);
      let system;
      if (el.scrollLeft > 0) {
          system = 'positive'; // scroll is a positive number from the left edge
      }
      else {
          el.scrollLeft = 50;
          if (el.scrollLeft > 0) {
              system = 'reverse'; // scroll is a positive number from the right edge
          }
          else {
              system = 'negative'; // scroll is a negative number from the right edge
          }
      }
      el.remove();
      return system;
  }

  class StandardEvent extends BaseComponent {
      constructor() {
          super(...arguments);
          // memo
          this.buildPublicEvent = memoize((context, eventDef, eventInstance) => new EventImpl(context, eventDef, eventInstance));
          this.handleEl = (el) => {
              this.el = el;
              setRef(this.props.elRef, el);
              if (el) {
                  setElEventRange(el, this.props.eventRange);
              }
          };
      }
      render() {
          const { props, context } = this;
          const { options } = context;
          const { eventRange } = props;
          const eventUi = eventRange.ui;
          const timeFormat = options.eventTimeFormat || props.defaultTimeFormat;
          const timeText = props.forcedTimeText ?? buildEventRangeTimeText(timeFormat, eventRange, // just for def/instance
          props.slicedStart, props.slicedEnd, props.isStart, props.isEnd, context, props.defaultDisplayEventTime, props.defaultDisplayEventEnd);
          const [tag, attrs, isInteractive] = getEventTagAndAttrs(eventRange, context);
          const eventApi = this.buildPublicEvent(context, eventRange.def, eventRange.instance);
          const isDraggable = !props.disableDragging && computeEventRangeDraggable(eventRange, context);
          const isBlock = /row|column/.test(props.display);
          const subcontentRenderProps = {
              event: eventApi,
              isNarrow: props.isNarrow || false,
              isShort: props.isShort || false,
              timeText,
          };
          const renderProps = {
              event: eventApi, // make stable. everything else atomic. FYI, eventRange unfortunately gets reconstructed a lot, but def/instance is stable
              view: context.viewApi,
              timeText: timeText,
              color: eventUi.color || options.eventColor,
              contrastColor: eventUi.contrastColor || options.eventContrastColor,
              isDraggable,
              isStartResizable: !props.disableResizing && props.isStart && eventUi.durationEditable && options.eventResizableFromStart,
              isEndResizable: !props.disableResizing && props.isEnd && eventUi.durationEditable,
              isMirror: props.isMirror,
              isStart: Boolean(props.isStart),
              isEnd: Boolean(props.isEnd),
              isFirst: Boolean(props.isFirst),
              isLast: Boolean(props.isLast),
              isPast: Boolean(props.isPast), // TODO: don't cast. getDateMeta does it
              isFuture: Boolean(props.isFuture), // TODO: don't cast. getDateMeta does it
              isToday: Boolean(props.isToday), // TODO: don't cast. getDateMeta does it
              isSelected: Boolean(props.isSelected),
              isDragging: Boolean(props.isDragging),
              isResizing: Boolean(props.isResizing),
              isInteractive,
              isNarrow: props.isNarrow || false,
              isShort: props.isShort || false,
              level: props.level || 0,
              timeClass: joinClassNames(generateClassName(options.eventTimeClass, subcontentRenderProps), isBlock && generateClassName(options.blockEventTimeClass, subcontentRenderProps), props.display === 'row' && generateClassName(options.rowEventTimeClass, subcontentRenderProps), props.display === 'column' && generateClassName(options.columnEventTimeClass, subcontentRenderProps), props.display === 'list-item' && generateClassName(options.listItemEventTimeClass, subcontentRenderProps)),
              titleClass: joinClassNames(generateClassName(options.eventTitleClass, subcontentRenderProps), isBlock && generateClassName(options.blockEventTitleClass, subcontentRenderProps), props.display === 'row' && generateClassName(options.rowEventTitleClass, subcontentRenderProps), props.display === 'column' && generateClassName(options.columnEventTitleClass, subcontentRenderProps), props.display === 'list-item' && generateClassName(options.listItemEventTitleClass, subcontentRenderProps), props.display === 'row' && options.rowEventTitleSticky && classNames.stickyS, props.display === 'column' && options.columnEventTitleSticky && classNames.stickyT),
              options: { eventOverlap: Boolean(options.eventOverlap) },
          };
          const outerClassName = joinClassNames(// already includes eventClass below
          isBlock && generateClassName(options.blockEventClass, renderProps), props.display === 'row' && generateClassName(options.rowEventClass, renderProps), props.display === 'column' && generateClassName(options.columnEventClass, renderProps), props.display === 'list-item' && generateClassName(options.listItemEventClass, renderProps), eventUi.className, props.className, props.display === 'column'
              ? classNames.flexCol
              : classNames.flexRow, (eventRange.def.url || isDraggable) && classNames.cursorPointer, classNames.internalEvent, props.isMirror && classNames.internalEventMirror, isDraggable && classNames.internalEventDraggable, renderProps.isSelected && classNames.internalEventSelected, (renderProps.isStartResizable || renderProps.isEndResizable) && classNames.internalEventResizable);
          const beforeClassName = joinClassNames(generateClassName(options.eventBeforeClass, renderProps), isBlock && generateClassName(options.blockEventBeforeClass, renderProps), props.display === 'row' && generateClassName(options.rowEventBeforeClass, renderProps), props.display === 'column' && generateClassName(options.columnEventBeforeClass, renderProps), props.display === 'list-item' && generateClassName(options.listItemEventBeforeClass, renderProps));
          const afterClassName = joinClassNames(generateClassName(options.eventAfterClass, renderProps), isBlock && generateClassName(options.blockEventAfterClass, renderProps), props.display === 'row' && generateClassName(options.rowEventAfterClass, renderProps), props.display === 'column' && generateClassName(options.columnEventAfterClass, renderProps), props.display === 'list-item' && generateClassName(options.listItemEventAfterClass, renderProps));
          const innerClassName = joinClassNames(generateClassName(options.eventInnerClass, renderProps), isBlock && generateClassName(options.blockEventInnerClass, renderProps), props.display === 'row' && generateClassName(options.rowEventInnerClass, renderProps), props.display === 'column' && generateClassName(options.columnEventInnerClass, renderProps), props.display === 'list-item' && generateClassName(options.listItemEventInnerClass, renderProps), !props.disableLiquid && classNames.liquid);
          const beforeContent = props.display === 'row' && options.rowEventBeforeContent;
          const afterContent = props.display === 'row' && options.rowEventAfterContent;
          return (u$1(ContentContainer, { tag: tag, attrs: {
                  ...props.attrs,
                  ...attrs,
                  // HACK because this event-element gets attached to root during some dragging
                  dir: (props.isDragging && options.direction === 'rtl') ? 'rtl' : undefined,
              }, className: outerClassName, style: {
                  '--fc-event-color': renderProps.color,
                  '--fc-event-contrast-color': renderProps.contrastColor,
              }, elRef: this.handleEl, renderProps: renderProps, generatorName: "eventContent", customGenerator: options.eventContent, defaultGenerator: renderInnerContent$2, classNameGenerator: options.eventClass, didMount: options.eventDidMount, willUnmount: options.eventWillUnmount, children: (InnerContent) => (u$1(S, { children: [Boolean(renderProps.isSelected && isBlock) && (u$1("div", { className: props.display === 'column'
                              ? classNames.hitX
                              : classNames.hitY })), (beforeClassName || beforeContent) && (u$1("div", { className: joinClassNames(beforeClassName, !props.disableZindexes && classNames.z1, renderProps.isStartResizable && joinClassNames(props.display === 'column'
                              ? classNames.cursorResizeT
                              : classNames.cursorResizeS, 
                          // these classnames required for dnd
                          classNames.internalEventResizer, classNames.internalEventResizerStart)), children: [beforeContent && (u$1(ContentContainer, { tag: 'div', style: { display: 'contents' }, attrs: { 'aria-hidden': true }, renderProps: renderProps, generatorName: undefined, customGenerator: beforeContent })), Boolean(renderProps.isStartResizable && renderProps.isSelected) && (u$1("div", { className: classNames.hit }))] })), u$1(InnerContent, { tag: "div", className: joinClassNames(innerClassName, !props.disableZindexes && classNames.z0) }), (afterClassName || afterContent) && (u$1("div", { className: joinClassNames(afterClassName, !props.disableZindexes && classNames.z1, renderProps.isEndResizable && joinClassNames(props.display === 'column'
                              ? classNames.cursorResizeB
                              : classNames.cursorResizeE, 
                          // these classnames required for dnd
                          classNames.internalEventResizer, classNames.internalEventResizerEnd)), children: [afterContent && (u$1(ContentContainer, { tag: 'div', style: { display: 'contents' }, attrs: { 'aria-hidden': true }, renderProps: renderProps, generatorName: undefined, customGenerator: afterContent })), Boolean(renderProps.isEndResizable && renderProps.isSelected) && (u$1("div", { className: classNames.hit }))] }))] })) }));
      }
      componentDidUpdate(prevProps) {
          if (this.el && this.props.eventRange !== prevProps.eventRange) {
              setElEventRange(this.el, this.props.eventRange);
          }
      }
  }
  StandardEvent.addPropsEquality({
      seg: isPropsEqualShallow,
  });
  function renderInnerContent$2(innerProps) {
      return (u$1(S, { children: [innerProps.timeText && (u$1("div", { className: innerProps.timeClass, children: innerProps.timeText })), u$1("div", { className: innerProps.titleClass, children: innerProps.event.title || u$1(S, { children: "\u00A0" }) })] }));
  }

  class Slicer {
      constructor() {
          this.sliceBusinessHours = memoize(this._sliceBusinessHours);
          this.sliceDateSelection = memoize(this._sliceDateSpan);
          this.sliceEventStore = memoize(this._sliceEventStore);
          this.sliceEventDrag = memoize(this._sliceInteraction);
          this.sliceEventResize = memoize(this._sliceInteraction);
          this.forceDayIfListItem = false; // hack
      }
      intersectDateSpan(dateSpan, activeRange, ...extraArgs) {
          const activeDateSpanRange = intersectRanges(dateSpan.range, activeRange);
          if (activeDateSpanRange) {
              const slicedDateSpan = { ...dateSpan, range: activeDateSpanRange };
              if (activeDateSpanRange.start.valueOf() !== dateSpan.range.start.valueOf()) {
                  delete slicedDateSpan.instantStartMs;
              }
              if (activeDateSpanRange.end.valueOf() !== dateSpan.range.end.valueOf()) {
                  delete slicedDateSpan.instantEndMs;
              }
              return slicedDateSpan;
          }
          return null;
      }
      sliceDateSpan(dateSpan, ...extraArgs) {
          return this.sliceRange(dateSpan.range, ...extraArgs);
      }
      sliceProps(props, dateProfile, nextDayThreshold, context, ...extraArgs) {
          let { eventUiBases } = props;
          let eventSegs = this.sliceEventStore(props.eventStore, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs);
          return {
              dateSelectionSegs: this.sliceDateSelection(props.dateSelection, dateProfile, nextDayThreshold, eventUiBases, context, ...extraArgs),
              businessHourSegs: this.sliceBusinessHours(props.businessHours, dateProfile, nextDayThreshold, context, ...extraArgs),
              fgEventSegs: eventSegs.fg,
              bgEventSegs: eventSegs.bg,
              eventDrag: this.sliceEventDrag(props.eventDrag, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs),
              eventResize: this.sliceEventResize(props.eventResize, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs),
              eventSelection: props.eventSelection,
          }; // TODO: give interactionSegs?
      }
      sliceNowDate(// does not memoize
      date, dateProfile, nextDayThreshold, context, ...extraArgs) {
          return this._sliceDateSpan({ range: { start: date, end: addMs(date, 1) }, allDay: false }, // add 1 ms, protect against null range
          dateProfile, nextDayThreshold, {}, context, ...extraArgs);
      }
      _sliceBusinessHours(businessHours, dateProfile, nextDayThreshold, context, ...extraArgs) {
          if (!businessHours) {
              return [];
          }
          return this._sliceEventStore(expandRecurring(businessHours, computeActiveRange(dateProfile, Boolean(nextDayThreshold)), context), {}, dateProfile, nextDayThreshold, ...extraArgs).bg;
      }
      _sliceEventStore(eventStore, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs) {
          if (eventStore) {
              let rangeRes = sliceEventStore(eventStore, eventUiBases, computeActiveRange(dateProfile, Boolean(nextDayThreshold)), nextDayThreshold);
              return {
                  bg: this.sliceEventRanges(rangeRes.bg, extraArgs),
                  fg: this.sliceEventRanges(rangeRes.fg, extraArgs),
              };
          }
          return { bg: [], fg: [] };
      }
      _sliceInteraction(interaction, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs) {
          if (!interaction) {
              return null;
          }
          let rangeRes = sliceEventStore(interaction.mutatedEvents, eventUiBases, computeActiveRange(dateProfile, Boolean(nextDayThreshold)), nextDayThreshold);
          return {
              segs: this.sliceEventRanges(rangeRes.fg, extraArgs),
              affectedInstances: interaction.affectedEvents.instances,
              isEvent: interaction.isEvent,
          };
      }
      _sliceDateSpan(dateSpan, dateProfile, nextDayThreshold, eventUiBases, context, ...extraArgs) {
          if (!dateSpan) {
              return [];
          }
          let activeRange = computeActiveRange(dateProfile, Boolean(nextDayThreshold));
          let slicedDateSpan = this.intersectDateSpan(dateSpan, activeRange, ...extraArgs);
          if (slicedDateSpan) {
              dateSpan = slicedDateSpan;
              let eventRange = fabricateEventRange(dateSpan, eventUiBases, context);
              let segs = this.sliceDateSpan(dateSpan, ...extraArgs);
              for (let seg of segs) {
                  seg.eventRange = eventRange;
              }
              return segs;
          }
          return [];
      }
      /*
      "complete" seg means it has component and eventRange
      */
      sliceEventRanges(eventRanges, extraArgs) {
          let segs = [];
          for (let eventRange of eventRanges) {
              segs.push(...this.sliceEventRange(eventRange, extraArgs));
          }
          return segs;
      }
      /*
      "complete" seg means it has component and eventRange
      */
      sliceEventRange(eventRange, extraArgs) {
          let dateRange = eventRange.range;
          // hack to make multi-day events that are being force-displayed as list-items to take up only one day
          if (this.forceDayIfListItem && eventRange.ui.display === 'list-item') {
              dateRange = {
                  start: dateRange.start,
                  end: addDays(dateRange.start, 1),
              };
          }
          let segs = this.sliceRange(dateRange, ...extraArgs); // !!!
          for (let seg of segs) {
              seg.eventRange = eventRange;
              seg.isStart = eventRange.isStart && seg.isStart;
              seg.isEnd = eventRange.isEnd && seg.isEnd;
          }
          return segs;
      }
  }
  /*
  for incorporating slotMinTime/slotMaxTime if appropriate
  TODO: should be part of DateProfile!
  TimelineDateProfile already does this btw
  */
  function computeActiveRange(dateProfile, isComponentAllDay) {
      let range = dateProfile.activeRange;
      if (isComponentAllDay) {
          return range;
      }
      return {
          start: addMs(range.start, dateProfile.slotMinTime.milliseconds),
          end: addMs(range.end, dateProfile.slotMaxTime.milliseconds - 864e5), // 864e5 = ms in a day
      };
  }

  class DayTableModel {
      constructor(daySeries, breakOnWeeks, dateEnv, majorUnit = '', activeRange) {
          this.daySeries = daySeries;
          this.dateEnv = dateEnv;
          this.majorUnit = majorUnit;
          this.activeRange = activeRange;
          let { dates } = daySeries;
          let daysPerRow;
          let firstDay;
          let rowCount;
          if (breakOnWeeks) {
              // count columns until the day-of-week repeats
              firstDay = dates[0].getUTCDay();
              for (daysPerRow = 1; daysPerRow < dates.length; daysPerRow += 1) {
                  if (dates[daysPerRow].getUTCDay() === firstDay) {
                      break;
                  }
              }
              rowCount = Math.ceil(dates.length / daysPerRow);
          }
          else {
              rowCount = 1;
              daysPerRow = dates.length;
          }
          this.rowCount = rowCount;
          this.colCount = daysPerRow;
          this.cellRows = this.buildCells();
          this.headerDates = this.buildHeaderDates();
      }
      buildCells() {
          let rows = [];
          for (let row = 0; row < this.rowCount; row += 1) {
              let cells = [];
              for (let col = 0; col < this.colCount; col += 1) {
                  cells.push(this.buildCell(row, col));
              }
              rows.push(cells);
          }
          return rows;
      }
      buildCell(row, col) {
          let date = this.daySeries.dates[row * this.colCount + col];
          return {
              key: date.toISOString(),
              date,
              isMajor: this.cellIsMajor(date),
              isDisabled: this.activeRange === null || (this.activeRange !== undefined && !rangeContainsMarker(this.activeRange, date)),
          };
      }
      cellIsMajor(dateMarker) {
          return this.majorUnit ? isMajorUnit(dateMarker, this.majorUnit, this.dateEnv) : false;
      }
      buildHeaderDates() {
          let dates = [];
          for (let col = 0; col < this.colCount; col += 1) {
              dates.push(this.cellRows[0][col].date);
          }
          return dates;
      }
  }
  function buildDayGridRanges(seriesRange, daysPerRow) {
      let ranges = [];
      if (seriesRange) {
          const { start, end } = seriesRange;
          let index = start;
          while (index < end) {
              let row = Math.floor(index / daysPerRow);
              let nextIndex = Math.min((row + 1) * daysPerRow, end);
              ranges.push({
                  row,
                  start: index % daysPerRow,
                  end: (nextIndex - 1) % daysPerRow + 1,
                  isStart: seriesRange.isStart && index === start,
                  isEnd: seriesRange.isEnd && nextIndex === end,
              });
              index = nextIndex;
          }
      }
      return ranges;
  }

  class DayTableSlicer extends Slicer {
      constructor() {
          super(...arguments);
          this.forceDayIfListItem = true;
      }
      sliceRange(dateRange, dayTableModel) {
          return buildDayGridRanges(dayTableModel.daySeries.sliceRange(dateRange), dayTableModel.colCount);
      }
  }
  class DaySeriesSlicer extends Slicer {
      constructor() {
          super(...arguments);
          this.forceDayIfListItem = true;
      }
      sliceRange(dateRange, daySeries) {
          return buildDayGridRanges(daySeries.sliceRange(dateRange), daySeries.cnt);
      }
  }

  // TODO: converge types with DayTableCell and DayCellContainer (the component) and refineRenderProps
  // the generation of DayTableCell will be distinct (for the BODY cells)
  // but can share some of the same types/utils
  // Date Cells
  // -------------------------------------------------------------------------------------------------
  const firstSunday = new Date(259200000);
  function buildDateRowConfigs(dates, datesRepDistinctDays, dateProfile, todayRange, dayHeaderFormat, // TODO: rename to dateHeaderFormat?
  context) {
      const rowConfig = buildDateRowConfig(dates, datesRepDistinctDays, dateProfile, todayRange, dayHeaderFormat, context);
      const majorUnit = computeMajorUnit(dateProfile, context.dateEnv);
      // HACK mutate isMajor
      // Skip 'day' majorUnit: when each header cell IS a day, every cell would match,
      // so there's no meaningful boundary to highlight (unlike timeline slots which can be sub-day).
      if (datesRepDistinctDays && majorUnit !== 'day') {
          for (const dataConfig of rowConfig.dataConfigs) {
              if (isMajorUnit(dataConfig.dateMarker, majorUnit, context.dateEnv)) {
                  dataConfig.renderProps.isMajor = true;
              }
          }
      }
      return [rowConfig];
  }
  /*
  Should this receive resource data attributes?
  Or ResourceApi object itself?
  */
  function buildDateRowConfig(dateMarkers, datesRepDistinctDays, dateProfile, todayRange, dayHeaderFormat, // TODO: rename to dateHeaderFormat?
  context, colSpan, isMajorMod, totalDateCnt) {
      return {
          isDateRow: true,
          renderConfig: buildDateRenderConfig(dayHeaderFormat, datesRepDistinctDays, context),
          dataConfigs: buildDateDataConfigs(dateMarkers, datesRepDistinctDays, dateProfile, todayRange, dayHeaderFormat, context, colSpan, undefined, undefined, undefined, undefined, isMajorMod, totalDateCnt)
      };
  }
  /*
  For header cells: how to connect w/ custom rendering
  Applies to all cells in a row
  */
  function buildDateRenderConfig(dayHeaderFormat, datesRepDistinctDays, context) {
      const { options } = context;
      return {
          generatorName: 'dayHeaderContent',
          customGenerator: options.dayHeaderContent,
          classNameGenerator: options.dayHeaderClass,
          innerClassNameGenerator: options.dayHeaderInnerClass,
          didMount: options.dayHeaderDidMount,
          willUnmount: options.dayHeaderWillUnmount,
          align: options.dayHeaderAlign,
          sticky: options._dayHeaderSticky,
          dayHeaderFormat,
          datesRepDistinctDays,
      };
  }
  const dowDates = [];
  for (let dow = 0; dow < 7; dow++) {
      dowDates.push(addDays(new Date(259200000), dow)); // start with Sun, 04 Jan 1970 00:00:00 GMT)
  }
  /*
  For header cells: data
  */
  function buildDateDataConfigs(dateMarkers, datesRepDistinctDays, dateProfile, todayRange, dayHeaderFormat, // TODO: rename to dateHeaderFormat?
  context, colSpan = 1, keyPrefix = '', extraRenderProps = {}, // TODO
  extraAttrs = {}, // TODO
  className = '', isMajorMod, 
  // how many dates the VIEW has, which is only different when a caller renders a subset:
  // resource views build one date row per resource, and per-date filtering can drop dates
  // that have no resources. nav links key off the view's count, not the subset's
  totalDateCnt = dateMarkers.length) {
      const { dateEnv, viewApi, options } = context;
      return datesRepDistinctDays
          ? dateMarkers.map((dateMarker, i) => {
              const dateMeta = getDateMeta(dateMarker, dateEnv, dateProfile, todayRange);
              const isMajor = isMajorMod != null && !(i % isMajorMod);
              const hasNavLink = options.navLinks && !dateMeta.isDisabled &&
                  totalDateCnt > 1; // don't show navlink to day if only one day
              const renderProps = {
                  ...dateMeta,
                  ...extraRenderProps,
                  isMajor,
                  isSticky: false, // HACK. gets overridden
                  inPopover: false,
                  hasNavLink,
                  view: viewApi,
              };
              const fullDateStr = buildDateStr(context, dateMarker);
              // for DayGridHeaderCell
              return {
                  key: keyPrefix + dateMarker.toUTCString(),
                  dateMarker,
                  renderProps,
                  attrs: {
                      'aria-label': fullDateStr,
                      ...(dateMeta.isToday ? { 'aria-current': 'date' } : {}), // TODO: assign undefined for nonexistent
                      'data-date': formatDayString(dateMarker),
                      ...extraAttrs,
                  },
                  // for navlink
                  innerAttrs: hasNavLink
                      ? buildNavLinkAttrs(context, dateMarker, undefined, fullDateStr)
                      : { 'aria-hidden': true }, // label already on cell
                  colSpan,
                  hasNavLink,
                  className,
              };
          })
          : dateMarkers.map((dateMarker, i) => {
              const dow = dateMarker.getUTCDay();
              const normDate = addDays(firstSunday, dow);
              const dateMeta = {
                  date: dateEnv.toDate(dateMarker),
                  dow,
                  isDisabled: false,
                  isFuture: false,
                  isPast: false,
                  isToday: false,
                  isOther: false,
              };
              const isMajor = isMajorMod != null && !(i % isMajorMod);
              const renderProps = {
                  ...dateMeta,
                  date: dowDates[dow],
                  isMajor,
                  isSticky: false, // HACK. gets overridden
                  inPopover: false,
                  hasNavLink: false,
                  view: viewApi,
                  ...extraRenderProps,
              };
              const fullWeekDayStr = joinDateTimeFormatParts(dateEnv.formatToParts(normDate, WEEKDAY_ONLY_FORMAT));
              // for DayGridHeaderCell
              return {
                  key: keyPrefix + String(dow),
                  dateMarker,
                  renderProps,
                  attrs: {
                      'aria-label': fullWeekDayStr,
                      ...extraAttrs,
                  },
                  // NOT a navlink
                  innerAttrs: {
                      'aria-hidden': true, // label already on cell
                  },
                  colSpan,
                  className,
              };
          });
  }

  /*
  TODO: make API where createRefMap() called
  */
  class RefMap {
      constructor(masterCallback, ignoreDeletes = false) {
          this.masterCallback = masterCallback;
          this.ignoreDeletes = ignoreDeletes;
          this.rev = '';
          this.current = new Map();
          this.callbacks = new Map;
          this.handleValue = (val, key) => {
              let { current, callbacks } = this;
              let priorExists = current.has(key);
              let priorVal = priorExists ? current.get(key) : null;
              let anyChange = false;
              // null signals deletion
              if (val === null) {
                  if (priorExists && !this.ignoreDeletes) {
                      current.delete(key);
                      callbacks.delete(key);
                      anyChange = true;
                  }
              }
              else {
                  anyChange = priorVal !== val;
                  current.set(key, val);
              }
              if (anyChange) {
                  this.rev = guid();
                  if (this.masterCallback) {
                      this.masterCallback(val, key, priorVal);
                  }
              }
          };
      }
      createRef(key) {
          let refCallback = this.callbacks.get(key);
          if (!refCallback) {
              refCallback = (val) => {
                  this.handleValue(val, key);
              };
              this.callbacks.set(key, refCallback);
          }
          return refCallback;
      }
  }

  class Ruler extends BaseComponent {
      constructor() {
          super(...arguments);
          this.elRef = M$1();
      }
      render() {
          return (u$1("div", { ref: this.elRef }));
      }
      componentDidMount() {
          this._isUnmounting = false;
          const { props } = this;
          const el = this.elRef.current;
          this.disconnectWidth = watchWidth(el, (width) => {
              if (this._isUnmounting)
                  return;
              setRef(props.widthRef, width);
          });
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.disconnectWidth();
          const { props } = this;
          if (props.widthRef) {
              setRef(props.widthRef, null);
          }
      }
  }

  /** Identifies a DayGrid seg by event instance and start, remaining stable if its end changes. */
  function getDayGridSegKey(seg) {
      return `${seg.eventRange.instance.instanceId}:${seg.start}`;
  }
  // DayGridRange utils (TODO: move)
  // -------------------------------------------------------------------------------------------------
  function splitSegsByRow(segs, rowCount) {
      const byRow = [];
      for (let row = 0; row < rowCount; row++) {
          byRow[row] = [];
      }
      for (const seg of segs) {
          byRow[seg.row].push(seg);
      }
      return byRow;
  }
  function splitInteractionByRow(ui, rowCount) {
      const byRow = [];
      if (!ui) {
          for (let row = 0; row < rowCount; row++) {
              byRow[row] = null;
          }
      }
      else {
          for (let row = 0; row < rowCount; row++) {
              byRow[row] = {
                  affectedInstances: ui.affectedInstances,
                  isEvent: ui.isEvent,
                  segs: [],
              };
          }
          for (const seg of ui.segs) {
              byRow[seg.row].segs.push(seg);
          }
      }
      return byRow;
  }

  class BgEvent extends BaseComponent {
      constructor() {
          super(...arguments);
          // memo
          this.buildPublicEvent = memoize((context, eventDef, eventInstance) => new EventImpl(context, eventDef, eventInstance));
          this.handleEl = (el) => {
              this.el = el;
              if (el) {
                  setElEventRange(el, this.props.eventRange);
              }
          };
      }
      render() {
          const { props, context } = this;
          const { eventRange } = props;
          const { options } = context;
          const eventUi = eventRange.ui;
          const eventApi = this.buildPublicEvent(context, eventRange.def, eventRange.instance);
          const subcontentRenderProps = {
              event: eventApi,
              isNarrow: props.isNarrow || false,
              isShort: props.isShort || false,
          };
          const renderProps = {
              event: eventApi,
              view: context.viewApi,
              timeText: '', // never display time
              color: eventUi.color || options.backgroundEventColor,
              contrastColor: eventUi.contrastColor,
              isDraggable: false,
              isStartResizable: false,
              isEndResizable: false,
              isMirror: false,
              isStart: props.isStart,
              isEnd: props.isEnd,
              isFirst: false,
              isLast: false,
              isPast: props.isPast,
              isFuture: props.isFuture,
              isToday: props.isToday,
              isSelected: false,
              isDragging: false,
              isResizing: false,
              isInteractive: false,
              level: 0,
              isNarrow: props.isNarrow || false,
              isShort: props.isShort || false,
              timeClass: '', // never display time
              titleClass: generateClassName(options.backgroundEventTitleClass, subcontentRenderProps),
              options: { eventOverlap: Boolean(options.eventOverlap) },
          };
          // does not include backgroundEventClass.. added below
          const outerClassName = joinClassNames(eventUi.className, classNames.fill, classNames.internalEvent, classNames.internalBgEvent, props.isVertical ? classNames.flexCol : classNames.flexRow);
          const innerClassName = joinClassNames(generateClassName(options.backgroundEventInnerClass, renderProps), classNames.liquid);
          return (u$1(ContentContainer, { tag: 'div', className: outerClassName, style: {
                  '--fc-event-color': renderProps.color,
                  '--fc-event-contrast-color': renderProps.contrastColor,
              }, defaultGenerator: renderInnerContent$1, elRef: this.handleEl, renderProps: renderProps, generatorName: "backgroundEventContent", customGenerator: options.backgroundEventContent, classNameGenerator: options.backgroundEventClass, didMount: options.backgroundEventDidMount, willUnmount: options.backgroundEventWillUnmount, children: (InnerContent) => (u$1(InnerContent, { tag: 'div', className: innerClassName })) }));
      }
      componentDidUpdate(prevProps) {
          if (this.el && this.props.eventRange !== prevProps.eventRange) {
              setElEventRange(this.el, this.props.eventRange);
          }
      }
  }
  function renderInnerContent$1(props) {
      let { title } = props.event;
      return title && (u$1("div", { className: props.titleClass, children: props.event.title }));
  }
  // Other types of fills
  // -------------------------------------------------------------------------------------------------
  function renderFill(fillType, options) {
      return (u$1("div", { className: joinClassNames(fillType === 'non-business' ? options.nonBusinessHoursClass :
              fillType === 'highlight' ? options.highlightClass : undefined, classNames.fill) }));
  }

  // Temporary stand-in for lateral cell border widths.
  // These should eventually be measured from the DOM.
  const COL_BORDER_WIDTH = 1;
  // Temporary stand-in for row-bottom border widths.
  // These should eventually be measured from the DOM.
  const ROW_BORDER_WIDTH = 1;

  const SPACE_FROM_VIEWPORT = 10;
  class MorePopover extends DateComponent {
      constructor() {
          super(...arguments);
          // memo
          this.getDateMeta = memoize(getDateMeta);
          this.closeRef = M$1();
          this.focusStartRef = M$1();
          this.focusEndRef = M$1();
          this.handleRootEl = (rootEl) => {
              this.rootEl = rootEl;
              if (rootEl) {
                  this.context.registerInteractiveComponent(this, {
                      el: rootEl,
                      useEventCenter: false,
                  });
              }
              else {
                  this.context.unregisterInteractiveComponent(this);
              }
          };
          // Triggered when the user clicks *anywhere* in the document, for the autoHide feature
          this.handleDocumentMouseDown = (ev) => {
              // only hide the popover if the click happened outside the popover
              const target = getEventTargetViaRoot(ev);
              if (!this.rootEl.contains(target)) {
                  this.handleClose();
              }
          };
          this.handleDocumentKeyDown = (ev) => {
              if (ev.key === 'Escape') {
                  this.handleClose();
              }
          };
          // for many different close techniques
          // cannot accept params because might receive a browser Event
          this.handleClose = () => {
              let { onClose } = this.props;
              if (onClose) {
                  onClose();
              }
          };
      }
      render() {
          let { props, context } = this;
          let { options, dateEnv, viewApi } = context;
          let { startDate, todayRange, dateProfile } = props;
          let dateMeta = this.getDateMeta(startDate, dateEnv, dateProfile, todayRange);
          let textParts = dateEnv.formatToParts(startDate, options.popoverFormat);
          let text = joinDateTimeFormatParts(textParts);
          const dayHeaderRenderProps = {
              ...dateMeta,
              isMajor: false,
              isNarrow: false,
              isSticky: false,
              inPopover: true,
              level: 0,
              hasNavLink: false,
              text,
              textParts,
              get weekdayText() { return findWeekdayText(textParts); },
              get dayNumberText() { return findDayNumberText(textParts); },
              view: viewApi,
              // TODO: should know about the resource!
          };
          const dayCellRenderProps = {
              ...dateMeta,
              isMajor: false,
              isNarrow: false,
              inPopover: true,
              hasNavLink: false,
              get weekdayText() { return findWeekdayText(textParts); },
              get dayNumberText() { return findDayNumberText(textParts); },
              get monthText() { return findMonthText(textParts); },
              view: viewApi,
              text: '',
              textParts: [],
              options: { businessHours: Boolean(options.businessHours) },
          };
          const fullDateStr = formatDayString(startDate);
          /*
          TODO: DRY with TimelineHeaderCell
          */
          const { dayHeaderAlign } = options;
          const align = typeof dayHeaderAlign === 'function'
              ? dayHeaderAlign({ level: 0, inPopover: true, isNarrow: false })
              : dayHeaderAlign;
          const isRtl = computeElIsRtl(props.alignEl);
          return $(u$1("div", { "data-date": fullDateStr, id: props.id, role: 'dialog', "aria-labelledby": props.titleId, className: joinClassNames(options.popoverClass, classNames.flexCol, classNames.popoverZ, classNames.abs, classNames.borderBoxRoot, classNames.internalPopover), style: {
                  // positioning is mutated directly in updateSize, HOWEVER, we don't want popover to start
                  // low on screen because might cause unnecessary scrollbars
                  top: 0,
                  left: 0,
              }, 
              // HACK because of portal
              dir: isRtl ? 'rtl' : undefined, "data-color-scheme": options.colorScheme || undefined, ref: this.handleRootEl, children: [u$1("div", { tabIndex: 0, style: { outline: 'none' }, ref: this.focusStartRef }), u$1("div", { className: joinClassNames(generateClassName(options.dayHeaderClass, dayHeaderRenderProps), classNames.flexCol, classNames.borderlessX, classNames.borderlessTop, align === 'center' ? classNames.alignCenter :
                          align === 'end' ? classNames.alignEnd :
                              classNames.alignStart), children: [u$1("div", { children: u$1(ContentContainer, { tag: "div", attrs: {
                                      id: props.titleId,
                                      // NOTE: more-popover never has nav-links
                                  }, generatorName: "dayHeaderContent", renderProps: dayHeaderRenderProps, customGenerator: options.dayHeaderContent, defaultGenerator: renderText, classNameGenerator: options.dayHeaderInnerClass, didMount: options.dayHeaderDidMount, willUnmount: options.dayHeaderWillUnmount }) }), u$1(ContentContainer, { tag: 'button', attrs: {
                                  'aria-label': options.closeHint,
                                  ...createAriaClickAttrs(this.handleClose)
                              }, elRef: this.closeRef, className: joinClassNames(options.popoverCloseClass, classNames.flexRow, classNames.cursorPointer), renderProps: {}, customGenerator: options.popoverCloseContent, generatorName: 'popoverCloseContent' })] }), u$1("div", { className: joinClassNames(generateClassName(options.dayCellClass, dayCellRenderProps), classNames.flexCol, classNames.borderless), children: u$1("div", { className: generateClassName(options.dayCellInnerClass, dayCellRenderProps), children: props.children }) }), u$1("div", { tabIndex: 0, style: { outline: 'none' }, ref: this.focusEndRef })] }), getAppendableRoot(props.alignEl));
      }
      queryHit(isRtl, positionLeft, positionTop, elWidth, elHeight) {
          let { rootEl, props } = this;
          if (positionLeft >= 0 && positionLeft < elWidth &&
              positionTop >= 0 && positionTop < elHeight) {
              return {
                  dateProfile: props.dateProfile,
                  dateSpan: {
                      allDay: !props.forceTimed,
                      range: {
                          start: props.startDate,
                          end: props.endDate,
                      },
                      ...props.dateSpanProps,
                  },
                  getDayEl: () => rootEl,
                  rect: {
                      left: 0,
                      top: 0,
                      right: elWidth,
                      bottom: elHeight,
                  },
                  layer: 1, // important when comparing with hits from other components
              };
          }
          return null;
      }
      componentDidMount() {
          document.addEventListener('mousedown', this.handleDocumentMouseDown);
          document.addEventListener('keydown', this.handleDocumentKeyDown);
          this.focusStartRef.current.addEventListener('focus', this.handleClose);
          this.focusEndRef.current.addEventListener('focus', this.handleClose);
          this.closeRef.current.focus({ preventScroll: true });
          this.updateSize();
      }
      componentWillUnmount() {
          document.removeEventListener('mousedown', this.handleDocumentMouseDown);
          document.removeEventListener('keydown', this.handleDocumentKeyDown);
          this.focusStartRef.current.removeEventListener('focus', this.handleClose);
          this.focusEndRef.current.removeEventListener('focus', this.handleClose);
      }
      updateSize() {
          let { alignEl, alignParentTop } = this.props;
          let { rootEl: popoverEl } = this;
          const isRtl = computeElIsRtl(alignEl);
          // position relative to viewport
          const alignmentRect = computeClippedClientRect(alignEl);
          if (alignmentRect) {
              let popoverDims = popoverEl.getBoundingClientRect();
              // position relative to viewport
              let popoverVPTop = alignParentTop
                  // HACK: subtract 1 for DayGrid, which has borders on row-bottom. Only view that uses alignParentTop
                  ? alignEl.closest(alignParentTop).getBoundingClientRect().top - ROW_BORDER_WIDTH
                  : alignmentRect.top;
              let popoverVPLeft = isRtl ? alignmentRect.right - popoverDims.width : alignmentRect.left;
              // constrain
              popoverVPTop = Math.max(popoverVPTop, SPACE_FROM_VIEWPORT);
              popoverVPLeft = Math.min(popoverVPLeft, document.documentElement.clientWidth - SPACE_FROM_VIEWPORT - popoverDims.width);
              popoverVPLeft = Math.max(popoverVPLeft, SPACE_FROM_VIEWPORT);
              const { offsetParent } = popoverEl;
              // final popover position, relative to offsetParent
              let top;
              let left;
              // TODO: account for RTL
              if (!offsetParent || offsetParent === document.body) {
                  top = popoverVPTop + window.scrollY;
                  left = popoverVPLeft + window.scrollX;
              }
              else {
                  const offsetParentRect = offsetParent.getBoundingClientRect();
                  top = popoverVPTop - offsetParentRect.top + offsetParent.scrollTop;
                  left = popoverVPLeft - offsetParentRect.left + offsetParent.scrollLeft;
              }
              applyStyle(popoverEl, { top, left });
          }
      }
  }
  // TODO: DRY
  function renderText(renderProps) {
      return renderProps.text;
  }

  // NOTE: numeric span algebra (intersection, subtraction, unions, sorted
  // searches) lives in seg-placement/span-math.ts; CoordRange is structurally
  // identical to its LateralSpan.
  // { eventRange }
  // -------------------------------------------------------------------------------------------------
  function computeEarliestStart(segs) {
      return segs.reduce(pickEarliestStart).eventRange.range.start;
  }
  function computeLatestEnd(segs) {
      return segs.reduce(pickLatestEnd).eventRange.range.end;
  }
  function pickEarliestStart(r0, r1) {
      return r0.eventRange.range.start < r1.eventRange.range.start ? r0 : r1;
  }
  function pickLatestEnd(r0, r1) {
      return r0.eventRange.range.end > r1.eventRange.range.end ? r0 : r1;
  }

  /*
  Renders only the themed, customizable more-link presentation. Interaction,
  popover state, and date-range semantics belong to MoreLinkContainer.
  */
  class MoreLinkTrigger extends BaseComponent {
      render() {
          const { props, context } = this;
          const { options } = context;
          const renderProps = buildMoreLinkRenderProps(props.num, props.isNarrow, props.isMicro, props.display, context);
          return (u$1(ContentContainer, { tag: 'div', elRef: props.elRef, className: joinClassNames(generateClassName(props.display === 'row'
                  ? options.rowMoreLinkClass
                  : options.columnMoreLinkClass, renderProps), props.className, props.display === 'row'
                  ? classNames.flexRow
                  : classNames.flexCol, classNames.internalMoreLink, classNames.cursorPointer), style: props.style, attrs: props.attrs, renderProps: renderProps, generatorName: "moreLinkContent", customGenerator: options.moreLinkContent, defaultGenerator: renderMoreLinkText, classNameGenerator: options.moreLinkClass, didMount: props.didMount, willUnmount: props.willUnmount, children: (InnerContent) => (u$1(InnerContent, { tag: 'div', className: joinClassNames(generateClassName(options.moreLinkInnerClass, renderProps), generateClassName(props.display === 'row'
                      ? options.rowMoreLinkInnerClass
                      : options.columnMoreLinkInnerClass, renderProps), props.display === 'row'
                      ? classNames.stickyS
                      : classNames.stickyT) })) }));
      }
  }
  class MoreLinkContainer extends BaseComponent {
      constructor() {
          super(...arguments);
          this.state = {
              isPopoverOpen: false,
          };
          this.handleLinkEl = (linkEl) => {
              this.linkEl = linkEl;
              if (this.props.elRef) {
                  setRef(this.props.elRef, linkEl);
              }
          };
          this.handleClick = (ev) => {
              let { props, context } = this;
              let { dateEnv, options } = context;
              let { moreLinkClick } = options;
              let date = computeRange(props).start;
              function buildPublicSeg(seg) {
                  let { def, instance, range } = seg.eventRange;
                  const start = buildRangeEdgeOutput(range.start, range.instantStartMs, dateEnv);
                  const end = buildRangeEdgeOutput(range.end, range.instantEndMs, dateEnv);
                  return {
                      event: new EventImpl(context, def, instance),
                      start: start.date,
                      end: end.date,
                      isStart: seg.isStart,
                      isEnd: seg.isEnd,
                  };
              }
              if (typeof moreLinkClick === 'function') {
                  moreLinkClick = moreLinkClick({
                      date: dateEnv.toDate(date),
                      allDay: Boolean(props.allDayDate),
                      allSegs: props.segs.map(buildPublicSeg),
                      hiddenSegs: props.hiddenSegs.map(buildPublicSeg),
                      jsEvent: ev,
                      view: context.viewApi,
                  });
              }
              if (!moreLinkClick || moreLinkClick === 'popover') {
                  this.setState({ isPopoverOpen: true });
              }
              else if (typeof moreLinkClick === 'string') { // a view name
                  context.calendarApi.zoomTo(date, moreLinkClick);
              }
          };
          this.handlePopoverClose = () => {
              if (this.linkEl) { // was null sometimes when initiating drag-n-drop would hide the popover
                  this.linkEl.focus();
              }
              this.setState({ isPopoverOpen: false });
          };
      }
      render() {
          const { props, state, context } = this;
          const { options, baseId } = context;
          const moreCnt = props.hiddenSegs.length;
          const range = computeRange(props);
          const popoverId = baseId + 'popover-' + range.start.toISOString();
          const renderProps = buildMoreLinkRenderProps(moreCnt, props.isNarrow, props.isMicro, props.display, context);
          const hint = formatWithOrdinals(options.moreLinkHint, [moreCnt], renderProps.longText);
          return (u$1(S, { children: [Boolean(moreCnt) && (u$1(MoreLinkTrigger, { num: moreCnt, display: props.display, isNarrow: props.isNarrow, isMicro: props.isMicro, elRef: this.handleLinkEl, className: props.className, style: props.style, attrs: {
                          ...props.attrs,
                          ...createAriaClickAttrs(this.handleClick),
                          title: hint,
                          'role': 'button',
                          'aria-haspopup': 'dialog',
                          'aria-expanded': state.isPopoverOpen,
                          'aria-controls': state.isPopoverOpen ? popoverId : undefined,
                      }, didMount: options.moreLinkDidMount, willUnmount: options.moreLinkWillUnmount })), state.isPopoverOpen && (u$1(MorePopover, { id: popoverId, titleId: popoverId + '-title', startDate: range.start, endDate: range.end, dateProfile: props.dateProfile, todayRange: props.todayRange, dateSpanProps: props.dateSpanProps, alignEl: props.alignElRef ? props.alignElRef.current : this.linkEl, alignParentTop: props.alignParentTop, forceTimed: props.forceTimed, onClose: this.handlePopoverClose, children: props.popoverContent() }))] }));
      }
  }
  function renderMoreLinkText(props) {
      return props.text;
  }
  function buildMoreLinkRenderProps(num, isNarrow, isMicro, display, context) {
      const { viewApi, options, calendarApi } = context;
      const numericText = `+${num}`; // TODO: offer hook or i18n?
      const longText = typeof options.moreLinkText === 'function' // TODO: eventually use formatWithOrdinals
          ? options.moreLinkText.call(calendarApi, num)
          : `${numericText} ${options.moreLinkText}`;
      return {
          num,
          numericText,
          longText,
          text: (isMicro || display === 'column') ? numericText : longText,
          isNarrow,
          view: viewApi,
      };
  }
  function computeRange(props) {
      if (props.allDayDate) {
          return {
              start: props.allDayDate,
              end: addDays(props.allDayDate, 1),
          };
      }
      return {
          start: computeEarliestStart(props.hiddenSegs),
          end: computeLatestEnd(props.hiddenSegs),
      };
  }

  const DEFAULT_TABLE_EVENT_TIME_FORMAT = createFormatter({
      hour: 'numeric',
      minute: '2-digit',
      omitZeroMinute: true,
      meridiem: 'narrow',
  });
  function hasListItemDisplay(range, eventRange) {
      let { display } = eventRange.ui;
      return display === 'list-item' || (display === 'auto' &&
          !eventRange.def.allDay &&
          (range.end - range.start) === 1 && // single-day
          range.isStart && // "
          range.isEnd // "
      );
  }

  // All positioned layers share the DayGrid row's isolated stacking context.
  const DAY_GRID_NON_BUSINESS_Z_CLASS = classNames.z1;
  const DAY_GRID_BG_EVENT_Z_CLASS = classNames.z2;
  const DAY_GRID_HIGHLIGHT_Z_CLASS = classNames.z3;
  const DAY_GRID_CELL_CONTENT_Z_CLASS = classNames.z4;
  const DAY_GRID_EVENT_Z_CLASS = classNames.z5;
  const DAY_GRID_INTERACTION_Z_CLASS = classNames.z1000;

  class DayGridMoreLink extends BaseComponent {
      render() {
          let { props } = this;
          return (u$1(MoreLinkContainer, { display: 'row', className: joinClassNames(props.className, DAY_GRID_CELL_CONTENT_Z_CLASS), isNarrow: props.isNarrow, isMicro: props.isMicro, dateProfile: props.dateProfile, todayRange: props.todayRange, allDayDate: props.allDayDate, segs: props.segs, hiddenSegs: props.hiddenSegs, alignElRef: props.alignElRef, alignParentTop: props.alignParentTop, dateSpanProps: props.dateSpanProps, popoverContent: () => (u$1(S, { children: props.segs.map((seg) => {
                      let { eventRange } = seg;
                      let { instanceId } = eventRange.instance;
                      let isDragging = Boolean(props.eventDrag && props.eventDrag.affectedInstances[instanceId]);
                      let isResizing = Boolean(props.eventResize && props.eventResize.affectedInstances[instanceId]);
                      let isInvisible = isDragging || isResizing;
                      return (u$1("div", { style: {
                              visibility: isInvisible ? 'hidden' : undefined,
                          }, children: u$1(StandardEvent, { display: hasListItemDisplay(seg, eventRange) ? 'list-item' : 'row', eventRange: eventRange, isStart: seg.isStart, isEnd: seg.isEnd, isDragging: isDragging, isResizing: isResizing, isMirror: false, isSelected: instanceId === props.eventSelection, defaultTimeFormat: DEFAULT_TABLE_EVENT_TIME_FORMAT, defaultDisplayEventEnd: false, ...getEventRangeMeta(eventRange, props.todayRange) }) }, instanceId));
                  }) })) }));
      }
  }

  class DayGridCell extends DateComponent {
      constructor() {
          super(...arguments);
          // memo
          this.getDateMeta = memoize(getDayGridCellDateMeta);
          this.refineRenderProps = memoizeObjArg(refineRenderProps);
          // ref
          this.rootElRef = M$1();
          this.handleBodyEl = (bodyEl) => {
              if (this.disconnectBodyHeight) {
                  this.disconnectBodyHeight();
                  this.disconnectBodyHeight = undefined;
                  this.headerHeight = undefined;
                  setRef(this.props.headerHeightRef, null);
                  setRef(this.props.mainHeightRef, null);
              }
              // Print cells don't need this screen-only measurement.
              if (bodyEl && (this.props.headerHeightRef || this.props.mainHeightRef)) {
                  // we want to fire on ANY size change, because we do more advanced stuff
                  this.disconnectBodyHeight = watchSize(bodyEl, (_bodyWidth, bodyHeight) => {
                      if (this._isUnmounting) {
                          return;
                      }
                      const { props } = this;
                      const rootEl = this.rootElRef.current;
                      // A queued resize can outlive the cell element.
                      if (!rootEl) {
                          return;
                      }
                      const mainRect = bodyEl.getBoundingClientRect();
                      const rootRect = rootEl.getBoundingClientRect();
                      const headerHeight = mainRect.top - rootRect.top;
                      if (!isDimsEqual(this.headerHeight, headerHeight)) {
                          this.headerHeight = headerHeight;
                          setRef(props.headerHeightRef, headerHeight);
                      }
                      /*
                      Reported in every mode, even though only a liquid cell's placement
                      consumes it. The body keeps the same element and the same observer when
                      `fgLiquidHeight` flips, and switching it between `grow` and `liquid`
                      need not change its height at all, so a mode-conditional report would
                      leave a newly liquid cell waiting for an unrelated resize before it
                      ever learned its own ceiling.
                      */
                      setRef(props.mainHeightRef, bodyHeight);
                  });
              }
          };
      }
      render() {
          let { props, context } = this;
          let { options, dateEnv } = context;
          const { tableMode } = props;
          // TODO: memoize this
          const isMonthStart = props.showDayNumber &&
              shouldDisplayMonthStart(props.date, props.dateProfile.currentRange, dateEnv);
          const dateMeta = this.getDateMeta(props.date, dateEnv, props.dateProfile, props.todayRange, props.isDisabled);
          const baseClassName = joinClassNames(classNames.borderlessTop, classNames.borderlessEnd, !props.borderStart && classNames.borderlessStart, !(tableMode && props.borderBottom) && classNames.borderlessBottom, !tableMode && props.width == null && classNames.liquid, !tableMode && classNames.flexCol, classNames.rel, classNames.noMargin, classNames.noPadding);
          const CellTag = tableMode ? 'td' : 'div';
          const cellStyle = tableMode ? undefined : { width: props.width };
          const hasNavLink = options.navLinks;
          const renderProps = this.refineRenderProps({
              date: props.date,
              isMajor: props.isMajor,
              isNarrow: props.isNarrow,
              dateMeta: dateMeta,
              hasLabel: props.showDayNumber,
              hasMonthLabel: isMonthStart,
              hasNavLink,
              renderProps: props.renderProps,
              viewApi: context.viewApi,
              dateEnv: context.dateEnv,
              monthStartFormat: options.monthStartFormat,
              dayCellFormat: options.dayCellFormat,
              businessHours: Boolean(options.businessHours),
          });
          if (dateMeta.isDisabled) {
              return (u$1(CellTag, { role: 'gridcell', "aria-disabled": true, className: joinClassNames(generateClassName(options.dayCellClass, renderProps), props.className, baseClassName), style: cellStyle, children: props.fills }));
          }
          const fullDateStr = buildDateStr(context, props.date);
          return (u$1(ContentContainer, { tag: CellTag, elRef: this.rootElRef, className: joinClassNames(props.className, baseClassName), attrs: {
                  ...props.attrs,
                  role: 'gridcell',
                  'aria-label': fullDateStr,
                  ...(renderProps.isToday ? { 'aria-current': 'date' } : {}),
                  'data-date': formatDayString(props.date),
              }, style: cellStyle, renderProps: renderProps, generatorName: "dayCellTopContent" // !!! for top
              , customGenerator: options.dayCellTopContent /* !!! for top */, defaultGenerator: renderTopInner, classNameGenerator: options.dayCellClass, didMount: options.dayCellDidMount, willUnmount: options.dayCellWillUnmount, children: (InnerContent) => (u$1(S, { children: [props.fills, u$1("div", { className: joinClassNames(classNames.rel, // puts it above bg-fills, which are positioned on TOP of this component :|
                          DAY_GRID_CELL_CONTENT_Z_CLASS, generateClassName(options.dayCellTopClass, renderProps)), children: props.showDayNumber && (u$1(InnerContent // the dayCellTopContent
                          , { tag: 'div', attrs: hasNavLink
                                  ? buildNavLinkAttrs(context, props.date, undefined, fullDateStr)
                                  : { 'aria-hidden': true } // label already on cell
                              , className: generateClassName(options.dayCellTopInnerClass, renderProps) })) }), u$1("div", { className: joinClassNames(!tableMode && classNames.flexCol, !tableMode && (props.fgLiquidHeight ? classNames.liquid : classNames.grow), tableMode && classNames.printCellContentMinHeight), ref: this.handleBodyEl, children: [u$1("div", { className: joinClassNames(classNames.rel, // origin for this cell's foreground event wrappers
                                  generateClassName(options.dayCellInnerClass, renderProps)), style: { minHeight: props.fgHeight }, children: props.fg }), u$1(DayGridMoreLink, { className: classNames.rel, allDayDate: props.date, segs: props.segs, hiddenSegs: props.hiddenSegs, alignElRef: this.rootElRef, alignParentTop: props.showDayNumber
                                      ? '[role=row]'
                                      : `.${classNames.internalView}`, dateSpanProps: props.dateSpanProps, dateProfile: props.dateProfile, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, todayRange: props.todayRange, isNarrow: props.isNarrow, isMicro: props.isMicro })] }), u$1("div", { className: joinClassNames(classNames.rel, // puts it above bg-fills
                          DAY_GRID_CELL_CONTENT_Z_CLASS, generateClassName(options.dayCellBottomClass, renderProps)) })] })) }));
      }
      componentDidMount() {
          this._isUnmounting = false;
      }
      componentWillUnmount() {
          this._isUnmounting = true;
      }
  }
  // Utils
  // -------------------------------------------------------------------------------------------------
  function getDayGridCellDateMeta(date, dateEnv, dateProfile, todayRange, isDisabled) {
      return {
          ...getDateMeta(date, dateEnv, dateProfile, todayRange),
          isDisabled,
      };
  }
  function renderTopInner(props) {
      return props.text || u$1(S, { children: "\u00A0" }); // TODO: DRY?
  }
  function shouldDisplayMonthStart(date, currentRange, dateEnv) {
      const { start: currentStart, end: currentEnd } = currentRange;
      const currentEndIncl = addMs(currentEnd, -1);
      const currentFirstYear = dateEnv.getYear(currentStart);
      const currentFirstMonth = dateEnv.getMonth(currentStart);
      const currentLastYear = dateEnv.getYear(currentEndIncl);
      const currentLastMonth = dateEnv.getMonth(currentEndIncl);
      // spans more than one month?
      return !(currentFirstYear === currentLastYear && currentFirstMonth === currentLastMonth) &&
          Boolean(
          // first date in current view?
          date.valueOf() === currentStart.valueOf() ||
              // a month-start that's within the current range?
              (dateEnv.getDay(date) === 1 && date.valueOf() < currentEnd.valueOf()));
  }
  function refineRenderProps(raw) {
      let { date, dateEnv, hasLabel, hasMonthLabel, hasNavLink, businessHours } = raw;
      let textParts = [];
      let text = '';
      if (hasLabel) {
          textParts = dateEnv.formatToParts(date, hasMonthLabel ? raw.monthStartFormat : raw.dayCellFormat);
          text = joinDateTimeFormatParts(textParts);
      }
      return {
          ...raw.dateMeta,
          ...raw.renderProps,
          text,
          textParts,
          isMajor: raw.isMajor,
          isNarrow: raw.isNarrow,
          inPopover: false,
          hasNavLink,
          get weekdayText() { return findWeekdayText(textParts); },
          get dayNumberText() { return findDayNumberText(textParts); },
          get monthText() { return findMonthText(textParts); },
          options: { businessHours },
          view: raw.viewApi,
      };
  }

  class MeasuredHeightHarness extends C {
      constructor() {
          super(...arguments);
          this.rootElRef = M$1();
          this._isUnmounting = false;
      }
      render() {
          const { props } = this;
          return (u$1("div", { className: props.className, style: props.style, ref: this.rootElRef, children: props.children }));
      }
      componentDidMount() {
          this._isUnmounting = false;
          const rootEl = this.rootElRef.current; // TODO: make dynamic with useEffect
          this.disconnectHeight = watchHeight(rootEl, (height) => {
              if (this._isUnmounting)
                  return;
              this.height = height;
              setRef(this.props.heightRef, height);
          });
      }
      /*
      A wrapper can gain or lose measurement responsibility without remounting,
      because a row switches placement routes (screen<->print, for example) while
      reusing the same keyed nodes. The size observer only fires on an actual size
      change, so hand the newly attached ref what was already observed, and release
      the detached one.
      */
      componentDidUpdate(prevProps) {
          const { heightRef } = this.props;
          if (prevProps.heightRef !== heightRef) {
              setRef(prevProps.heightRef, null);
              if (this.height != null) {
                  setRef(heightRef, this.height);
              }
          }
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.disconnectHeight?.();
          setRef(this.props.heightRef, null);
      }
  }

  /**
   * Pure lateral-span geometry shared by the seg-placement engine.
   *
   * A span is a half-open interval `[start, end)` on the lateral axis. The axis
   * can be discrete (DayGrid columns) or continuous (Timeline pixels). Exactly
   * adjacent spans never intersect.
   */
  function doSpansIntersect(a, b) {
      return a.start < b.end && b.start < a.end;
  }
  /** Returns the strict intersection; exactly adjacent spans do not intersect. */
  function intersectSpans(a, b) {
      const start = Math.max(a.start, b.start);
      const end = Math.min(a.end, b.end);
      return start < end ? { start, end } : null;
  }
  function getSpanLength(span) {
      return span.end - span.start;
  }
  /**
   * Finds every intersection within entries sorted by `start`. When the entries
   * are also pairwise non-intersecting, only the single entry before the lower
   * bound can straddle the span's start, so the scan begins one entry early.
   */
  function findIntersections(entries, span) {
      let index = findLowerBoundByStart(entries, span.start);
      if (index > 0) {
          index--;
      }
      const matches = [];
      for (; index < entries.length; index++) {
          const entry = entries[index];
          if (entry.start >= span.end) {
              break;
          }
          if (doSpansIntersect(entry, span)) {
              matches.push(entry);
          }
      }
      return matches;
  }
  /**
   * Computes the coverage set difference `span - covered`. The covered spans
   * must be sorted by `start` and pairwise non-overlapping.
   */
  function subtractCoveredSpans(span, covered) {
      const result = [];
      let cursor = span.start;
      for (const item of covered) {
          if (item.end <= cursor) {
              continue;
          }
          if (item.start >= span.end) {
              break;
          }
          if (item.start > cursor) {
              result.push({ start: cursor, end: Math.min(item.start, span.end) });
          }
          cursor = Math.max(cursor, item.end);
          if (cursor >= span.end) {
              break;
          }
      }
      if (cursor < span.end) {
          result.push({ start: cursor, end: span.end });
      }
      return result;
  }
  /** Maintains a sorted strict-overlap union; adjacent spans remain separate. */
  function addToUnion(spans, addition) {
      const result = [];
      let pending = { ...addition };
      let inserted = false;
      for (const span of spans) {
          if (span.end <= pending.start) {
              result.push(span);
          }
          else if (pending.end <= span.start) {
              if (!inserted) {
                  result.push(pending);
                  inserted = true;
              }
              result.push(span);
          }
          else {
              pending = {
                  start: Math.min(pending.start, span.start),
                  end: Math.max(pending.end, span.end),
              };
          }
      }
      if (!inserted) {
          result.push(pending);
      }
      spans.splice(0, spans.length, ...result);
  }
  /** Preserves increasing lateral-start order within a sorted entry list. */
  function insertLaterally(entries, entry) {
      entries.splice(findLowerBoundByStart(entries, entry.start), 0, entry);
  }
  function findLowerBoundByStart(entries, start) {
      let low = 0;
      let high = entries.length;
      while (low < high) {
          const middle = (low + high) >>> 1;
          if (entries[middle].start < start) {
              low = middle + 1;
          }
          else {
              high = middle;
          }
      }
      return low;
  }

  /**
   * Pure event-positioning kernel implementing measured logical repacking.
   *
   * Source segs own identity and event order. Slices own only lateral geometry,
   * while their outer array index is their dimensionless level. Limiting stays
   * primarily in logical slice-level space; the pixel path admits speculative
   * slices only through occupied logical territory, then monotonically prunes
   * the measured result against exact pixel and more-link boundaries.
   */
  /** Permissive epsilon for geometric coordinate and budget comparisons. */
  const GEOMETRY_TOLERANCE = 0.000001;
  /** Shared estimate for an event wrapper that has not reported a thickness. */
  const DEFAULT_UNMEASURED_EVENT_THICKNESS = 20;
  /** Shared estimate for a more-link wrapper that has not reported a thickness. */
  const DEFAULT_UNMEASURED_MORE_LINK_THICKNESS = 20;
  /**
   * Streams at most `maxLevels` into the initial structure and fires every
   * rejected slice back at those levels in event order.
   *
   * With slicing disabled, a failed slice hides whole. With slicing enabled,
   * every level independently offers its maximal free runs and the winning plan
   * balances exposed length against fragmentation. Every hidden slice grows a
   * coverage accumulator; with a level tax, only newly covered runs reserve the
   * bottom event level for a more link, evicting any slice already there.
   */
  function buildLevelLimitedLayout(segs, eventOrderStrict, eventSlicing, maxLevels, moreLinkLevelTax, sliceHeights) {
      const { segLevels, excludedSegs } = buildSegLevels(segs, eventOrderStrict, maxLevels);
      const placement = placeExtraSlicesInLevels(convertSegLevelsToWholeSlices(segLevels), convertSegsToWholeSlices(excludedSegs), eventOrderStrict, eventSlicing, moreLinkLevelTax);
      const resolution = resolveLevelCoords(placement.sliceLevels, sliceHeights);
      return {
          renderSlices: flatArray(placement.sliceLevels),
          hiddenSlices: placement.hiddenSlices,
          sliceLevels: placement.sliceLevels,
          sliceCoords: resolution.sliceCoords,
          isSettled: resolution.isSettled,
      };
  }
  /**
   * Resolves the bounded whole-slice frontier, then offers excluded slices back
   * to its occupied logical territory through slicing. Exact pixel pruning hides
   * any measured result that crosses the canvas or an existing more-link band.
   * Placement-only slices remain mounted as invisible measurement donors until
   * measured, preventing mount-measure cycles.
   *
   * `levelCapacity` bounds the initial DOM whole-slice candidates; later
   * slices begin hidden and unmeasured.
   */
  function buildPixelLimitedLayout(segs, eventOrderStrict, eventSlicing, sliceHeights, canvasHeight, levelCapacity, moreLinkHeight) {
      const { segLevels, excludedSegs } = buildSegLevels(segs, eventOrderStrict, levelCapacity);
      const domWholeSliceLevels = convertSegLevelsToWholeSlices(segLevels);
      const domExcludedWholeSlices = convertSegsToWholeSlices(excludedSegs);
      const wholeResolution = resolveLevelCoords(domWholeSliceLevels, sliceHeights, canvasHeight);
      // Until the canvas and the link probe report a size, mount only the bounded
      // whole-slice frontier so its measurements can arrive.
      if (canvasHeight == null || moreLinkHeight == null) {
          return {
              renderSlices: flatArray(domWholeSliceLevels),
              hiddenSlices: domExcludedWholeSlices,
              sliceLevels: domWholeSliceLevels,
              sliceCoords: wholeResolution.sliceCoords,
              isSettled: wholeResolution.isSettled,
          };
      }
      // Pending frontier wholes stay out of links until measured; beyond-frontier
      // wholes are definite logical exclusions and hide without measurement.
      const excludedWholeSlices = wholeResolution.excludedSlices.concat(domExcludedWholeSlices);
      excludedWholeSlices.sort(compareByEventOrder);
      // With slicing, the level tax punches link holes while preserving event
      // remainders; otherwise measured pruning makes the smarter pixel choice.
      const placement = placeExtraSlicesInLevels(wholeResolution.placementSliceLevels, excludedWholeSlices, eventOrderStrict, eventSlicing, 
      /* moreLinkLevelTax = */ eventSlicing ? 1 : 0, 
      /* requiresSlicing = */ true, 
      /* taxDeepestOccupiedLevel = */ true);
      const sliceResolution = resolveLevelCoords(placement.sliceLevels, sliceHeights);
      // More links always render. When one consumes the full budget or more, zero
      // is the deepest coordinate an intersecting event may reach.
      const moreLinkEventMax = Math.max(0, canvasHeight - moreLinkHeight);
      // Remove exact canvas and more-link overflows from the coordinated layout.
      const pixelPrunedSlices = prunePixelLimitedSliceLevels(placement.sliceLevels, placement.hiddenSlices, sliceResolution.sliceCoords, sliceHeights, canvasHeight, moreLinkEventMax);
      // Keep all frontier wholes and placement-added slices mounted as measurement
      // donors; missing coordinates make rejected or pending slices invisible.
      // Disjoint: requiresSlicing bars whole re-insertion, so every added slice is
      // a freshly cut object, never a frontier whole.
      const renderSlices = flatArray(domWholeSliceLevels).concat(placement.addedSlices);
      // Frontier wholes resolve in the whole pass and every placement-added slice
      // resolves in the placement pass, so together the two cover the render set.
      const isSettled = wholeResolution.isSettled && sliceResolution.isSettled;
      return {
          renderSlices,
          hiddenSlices: pixelPrunedSlices.concat(placement.hiddenSlices),
          sliceLevels: placement.sliceLevels,
          sliceCoords: sliceResolution.sliceCoords,
          isSettled,
      };
  }
  /* ========================================================================
   * Whole-source level construction
   * ===================================================================== */
  /** Builds whole-source logical levels without consulting any dimensions. */
  function buildSegLevels(segs, eventOrderStrict, maxLevels = Infinity) {
      const segLevels = [];
      const excludedSegs = [];
      for (const seg of segs) {
          const levelIndex = findPackedLevelIndex(segLevels, seg, eventOrderStrict);
          if (levelIndex >= maxLevels) {
              excludedSegs.push(seg);
          }
          else {
              while (segLevels.length <= levelIndex) {
                  segLevels.push([]);
              }
              insertLaterally(segLevels[levelIndex], seg);
          }
      }
      return { segLevels, excludedSegs };
  }
  /**
   * The packed level a span belongs to: the shallowest vacant level, or with
   * gap reuse forbidden, directly below the deepest intersecting occupant.
   * `levels.length` means a new level must open.
   */
  function findPackedLevelIndex(levels, span, orderStrict) {
      let levelIndex = 0;
      if (orderStrict) {
          for (let i = 0; i < levels.length; i++) {
              if (findIntersections(levels[i], span).length) {
                  levelIndex = i + 1;
              }
          }
      }
      else {
          while (levelIndex < levels.length &&
              findIntersections(levels[levelIndex], span).length) {
              levelIndex++;
          }
      }
      return levelIndex;
  }
  function convertSegLevelsToWholeSlices(segLevels) {
      return segLevels.map((level) => convertSegsToWholeSlices(level));
  }
  function convertSegsToWholeSlices(segs) {
      return segs.map(createWholeSlice);
  }
  /* ========================================================================
   * Slice-level coordinate resolution
   * ===================================================================== */
  /**
   * Resolves fixed logical levels without changing the input or its slices.
   * An unmeasured slice leaves the resolution unsettled; a measured bounded
   * rejection is final. Neither blocks later traversal entries, so excluding a
   * lower slice can let a later slice move upward. The returned placement
   * structure re-levels the admitted slices from scratch, compacted around
   * pending and excluded slices exactly like the coordinates. Each admitted
   * slice files below every admitted slice it intersects — never into a
   * shallower gap — so level order mirrors pixel stacking and strict input
   * order survives without consulting it.
   */
  function resolveLevelCoords(sliceLevels, sliceHeights, maxPixels = Infinity) {
      const placementSliceLevels = [];
      const sliceCoords = new Map();
      let isSettled = true;
      const excludedSlices = [];
      for (let levelIndex = 0; levelIndex < sliceLevels.length; levelIndex++) {
          for (const slice of sliceLevels[levelIndex]) {
              const sliceHeight = sliceHeights.get(getSliceKey(slice));
              if (sliceHeight === undefined) {
                  isSettled = false;
                  continue;
              }
              const { bottom: levelCoord, levelIndex: packedLevelIndex, } = computeLateralSpanPlacement(placementSliceLevels, slice, sliceCoords, sliceHeights);
              if (levelCoord + sliceHeight <=
                  maxPixels + GEOMETRY_TOLERANCE) {
                  // Repacking admitted slices merges levels, so keep lateral sort.
                  while (placementSliceLevels.length <= packedLevelIndex) {
                      placementSliceLevels.push([]);
                  }
                  insertLaterally(placementSliceLevels[packedLevelIndex], slice);
                  sliceCoords.set(getSliceKey(slice), levelCoord);
              }
              else {
                  excludedSlices.push(slice);
              }
          }
      }
      return { placementSliceLevels, sliceCoords, isSettled, excludedSlices };
  }
  /** Deepest measured, coordinated bottom and level among slices touching the span. */
  function computeLateralSpanPlacement(sliceLevels, span, sliceCoords, sliceHeights) {
      let bottom = 0;
      let levelIndex = 0;
      for (let i = 0; i < sliceLevels.length; i++) {
          const level = sliceLevels[i];
          for (const slice of findIntersections(level, span)) {
              const key = getSliceKey(slice);
              const sliceTop = sliceCoords.get(key);
              const sliceHeight = sliceHeights.get(key);
              if (sliceTop !== undefined && sliceHeight !== undefined) {
                  bottom = Math.max(bottom, sliceTop + sliceHeight);
                  levelIndex = i + 1;
              }
          }
      }
      return { bottom, levelIndex };
  }
  /** Deepest measured, coordinated bottom among slices touching the span. */
  function computeLateralSpanBottom(sliceLevels, span, sliceCoords, sliceHeights) {
      return computeLateralSpanPlacement(sliceLevels, span, sliceCoords, sliceHeights).bottom;
  }
  /** Recomputes every coordinated slice against the compacted visible set. */
  function recomputeVisibleCoords(sliceLevels, sliceHeights, sliceCoords) {
      const visibleLevels = sliceLevels.map((level) => level.filter((slice) => sliceCoords.has(getSliceKey(slice))));
      const freshCoords = resolveLevelCoords(visibleLevels, sliceHeights).sliceCoords;
      for (const [key, coord] of freshCoords) {
          sliceCoords.set(key, coord);
      }
  }
  /** Returns a measured slice's bottom, or `undefined` while it is pending. */
  function getSliceBottom(slice, sliceCoords, sliceHeights) {
      const key = getSliceKey(slice);
      const coord = sliceCoords.get(key);
      const height = sliceHeights.get(key);
      return coord === undefined || height === undefined
          ? undefined
          : coord + height;
  }
  /**
   * Monotonically removes measured slices that cross either the canvas boundary
   * or an active more-link boundary. Hiding a slice grows the more-link coverage;
   * only newly covered spans are fired through the remaining slices, so every
   * removal can expose more link-band intruders without reconsidering old spans.
   *
   * SIDE EFFECT: mutates `sliceCoords`. A removed coordinate is the renderer's
   * signal that the still-mounted slice is invisible. After every removal,
   * surviving coordinates are resolved again so later queue entries are tested
   * against the compacted pixel structure. Slices without a proposed coordinate
   * are ignored. Existing hidden slices seed the more-link coverage before the
   * first removal is considered.
   *
   * Returns the slices whose coordinates this pass removed, with no ordering
   * guarantee.
   */
  function prunePixelLimitedSliceLevels(sliceLevels, initialHiddenSlices, sliceCoords, sliceHeights, maxPixelHeight, moreLinkMaxPixelHeight) {
      const moreLinkGroups = [];
      const pixelPrunedSlices = [];
      const sliceHideQueue = [];
      let sliceHideIndex = 0;
      // Build the more-link coverage already established by logical placement.
      for (const hiddenSlice of initialHiddenSlices) {
          addHiddenSliceToGroups(moreLinkGroups, hiddenSlice);
      }
      // Seed the queue with canvas overflows and existing more-link intruders.
      enqueueViolators();
      // A head index preserves FIFO without shift()'s O(n) reindexing; pop() is LIFO.
      while (sliceHideIndex < sliceHideQueue.length) {
          const slice = sliceHideQueue[sliceHideIndex++];
          const sliceBottom = getSliceBottom(slice, sliceCoords, sliceHeights);
          // A missing coordinate means a prior queue entry already processed it, and
          // compaction from earlier removals can make a queued slice compliant again.
          if (sliceBottom === undefined ||
              !violatesPixelBoundary(slice, sliceBottom)) {
              continue;
          }
          // Removing the coordinate hides the still-mounted slice. The shared
          // coordinate primitive then compacts later visible slices around it.
          sliceCoords.delete(getSliceKey(slice));
          pixelPrunedSlices.push(slice);
          const newMoreLinkSpans = addHiddenSliceToGroups(moreLinkGroups, slice);
          recomputeVisibleCoords(sliceLevels, sliceHeights, sliceCoords);
          for (const newMoreLinkSpan of newMoreLinkSpans) {
              enqueueViolators(newMoreLinkSpan);
          }
      }
      return pixelPrunedSlices;
      /** Whether a measured bottom crosses the canvas or an intersecting link band. */
      function violatesPixelBoundary(slice, sliceBottom) {
          return sliceBottom > maxPixelHeight + GEOMETRY_TOLERANCE ||
              (sliceBottom > moreLinkMaxPixelHeight + GEOMETRY_TOLERANCE &&
                  findIntersections(moreLinkGroups, slice).length > 0);
      }
      /** Queues every measured violator, or only those touching one span. */
      function enqueueViolators(withinSpan) {
          for (const level of sliceLevels) {
              const candidates = withinSpan
                  ? findIntersections(level, withinSpan)
                  : level;
              for (const slice of candidates) {
                  const sliceBottom = getSliceBottom(slice, sliceCoords, sliceHeights);
                  if (sliceBottom !== undefined &&
                      violatesPixelBoundary(slice, sliceBottom)) {
                      sliceHideQueue.push(slice);
                  }
              }
          }
      }
  }
  /**
   * Fires event-ordered extras into a fixed set of logical levels. Repacking may
   * reuse gaps in the received levels but never creates additional levels.
   * By default, a more-link tax reserves the globally final level. Pixel flows
   * can instead reserve the deepest occupied level local to each link span and
   * require initial extras to expose some hidden coverage before admission.
   *
   * PRECONDITION: `extraSlices` is sorted by event order.
   *
   * SIDE EFFECT: mutates `sliceLevels`; callers transfer ownership of its outer
   * array and level arrays to this placement operation.
   */
  function placeExtraSlicesInLevels(sliceLevels, extraSlices, eventOrderStrict, eventSlicing, moreLinkLevelTax, 
  /** Whether initial extras must leave hidden coverage before admission. */
  requiresSlicing = false, 
  /** Whether each link taxes its deepest locally occupied level. */
  taxDeepestOccupiedLevel = false) {
      const addedSliceSet = new Set();
      // Hidden membership remains flat for whole-layout operations. More-link
      // groups duplicate that membership locally while also recording which
      // lateral territory has already fired its link tax.
      const hiddenSlices = [];
      const moreLinkGroups = [];
      const moreLinkReservations = [];
      const placementState = {
          levels: sliceLevels,
          moreLinkReservations,
          eventOrderStrict,
      };
      const work = [];
      pushFire(extraSlices, requiresSlicing);
      // LIFO runs newly created link reservations before older unrelated extras,
      // so an extra cannot insert into space that a fresh reservation will claim.
      while (work.length) {
          const item = work.pop();
          if (item.type === 'fire') {
              fire(item.slice, item.requiresSlicing);
          }
          else {
              fireMoreLink(item.span);
          }
      }
      return {
          sliceLevels,
          hiddenSlices,
          addedSlices: [...addedSliceSet],
      };
      /** Tries an allowed whole insertion before scored same-level slice plans. */
      function fire(slice, requiresSlicing) {
          if (!requiresSlicing) {
              const levelIndex = findInsertionLevel(slice, placementState);
              if (levelIndex !== null) {
                  insertLaterally(sliceLevels[levelIndex], slice);
                  addedSliceSet.add(slice);
                  return;
              }
          }
          if (!eventSlicing) {
              hide(slice);
              return;
          }
          const plan = findBestSlicePlan(slice, placementState, requiresSlicing);
          if (!plan) {
              hide(slice);
              return;
          }
          for (const visibleSlice of plan.slices) {
              insertLaterally(sliceLevels[plan.levelIndex], visibleSlice);
              addedSliceSet.add(visibleSlice);
          }
          for (const hiddenSlice of subtractSpansFromSlice(slice, plan.slices)) {
              hide(hiddenSlice);
          }
      }
      /** Adds hidden membership and fires links only over new accumulator coverage. */
      function hide(slice) {
          hiddenSlices.push(slice);
          // Only the set difference is fresh more-link territory; it can consist of
          // several disjoint runs.
          const newMoreLinkSpans = addHiddenSliceToGroups(moreLinkGroups, slice);
          if (moreLinkLevelTax) {
              for (let i = newMoreLinkSpans.length - 1; i >= 0; i--) {
                  work.push({ type: 'moreLink', span: newMoreLinkSpans[i] });
              }
          }
      }
      /**
       * Reserves one logical level over fresh accumulator coverage. The ordinary
       * flow taxes the final level; span-local mode taxes the deepest level with
       * an intersecting occupant, ignoring unrelated deeper territory.
       */
      function fireMoreLink(span) {
          if (!sliceLevels.length) {
              return;
          }
          let taxedLevelIndex = sliceLevels.length - 1;
          let victims = findIntersections(sliceLevels[taxedLevelIndex], span);
          if (taxDeepestOccupiedLevel) {
              while (!victims.length && taxedLevelIndex > 0) {
                  taxedLevelIndex--;
                  victims = findIntersections(sliceLevels[taxedLevelIndex], span);
              }
          }
          insertLaterally(moreLinkReservations, {
              ...span,
              levelIndex: taxedLevelIndex,
          });
          const taxedLevel = sliceLevels[taxedLevelIndex];
          for (const victim of victims) {
              taxedLevel.splice(taxedLevel.indexOf(victim), 1);
              addedSliceSet.delete(victim);
              if (eventSlicing) {
                  hide(intersectSlice(victim, span));
                  // The remainder has already satisfied the slicing requirement.
                  pushFire(subtractSpansFromSlice(victim, [span]), false);
              }
              else {
                  hide(victim);
              }
          }
      }
      /** Reversing preserves received order on the LIFO work stack. */
      function pushFire(slices, requiresSlicing) {
          for (let i = slices.length - 1; i >= 0; i--) {
              work.push({ type: 'fire', slice: slices[i], requiresSlicing });
          }
      }
  }
  /** Returns the shallowest vacant level within the slice's fence, if any. */
  function findInsertionLevel(slice, state) {
      const fence = computeLevelFence(slice, state);
      for (let levelIndex = fence.min; levelIndex < fence.maxExclusive; levelIndex++) {
          if (!findIntersections(state.levels[levelIndex], slice).length) {
              return levelIndex;
          }
      }
      return null;
  }
  /**
   * The level range where a slice may legally sit. The bottom reservation
   * closes its taxed level and everything deeper over link coverage; strict
   * event order additionally fences against intersecting neighbors' order.
   *
   * The pre-kernel SegHierarchy needed no upper fence: it inserted everything
   * in event order, so "stay below anything you touch" sufficed. Repacking
   * fires rejected extras after later-ordered slices are already committed,
   * which is what makes strict order two-sided here.
   */
  function computeLevelFence(slice, state) {
      const { levels } = state;
      let min = 0;
      let maxExclusive = levels.length;
      for (const reservation of findIntersections(state.moreLinkReservations, slice)) {
          maxExclusive = Math.min(maxExclusive, reservation.levelIndex);
      }
      if (state.eventOrderStrict) {
          for (let levelIndex = 0; levelIndex < levels.length; levelIndex++) {
              for (const other of findIntersections(levels[levelIndex], slice)) {
                  if (other.sourceSeg.orderIndex < slice.sourceSeg.orderIndex) {
                      min = Math.max(min, levelIndex + 1);
                  }
                  else if (other.sourceSeg.orderIndex > slice.sourceSeg.orderIndex) {
                      maxExclusive = Math.min(maxExclusive, levelIndex);
                  }
              }
          }
      }
      return { min, maxExclusive };
  }
  /* ========================================================================
   * Slice plans
   * ===================================================================== */
  const MAX_SLICES_PER_PLAN = 3;
  const EXTRA_SLICE_PENALTY = 0.15;
  /**
   * Scores the best one-, two-, or three-run insertion offered by each level.
   * Runs from different levels are deliberately never mixed into one plan.
   */
  function findBestSlicePlan(slice, state, requiresSlicing) {
      let selected = null;
      const sourceLength = getSpanLength(slice);
      for (let levelIndex = 0; levelIndex < state.levels.length; levelIndex++) {
          // findIntersections returns a fresh, start-sorted array, and addToUnion
          // replaces array contents without ever mutating a member, so link
          // reservations can be folded in without touching the actual level.
          const blockers = findIntersections(state.levels[levelIndex], slice);
          for (const reservation of state.moreLinkReservations) {
              if (levelIndex >= reservation.levelIndex) {
                  addToUnion(blockers, reservation);
              }
          }
          const runs = subtractSpansFromSlice(slice, blockers)
              .filter((run) => isWithinLevelFence(run, levelIndex, state))
              .sort((a, b) => getSpanLength(b) - getSpanLength(a) || a.start - b.start);
          let visibleLength = 0;
          for (let sliceCount = 1; sliceCount <= Math.min(MAX_SLICES_PER_PLAN, runs.length); sliceCount++) {
              visibleLength += getSpanLength(runs[sliceCount - 1]);
              // Full exposure leaves no hidden coverage, and visible length only
              // grows with more runs, so no longer plan can satisfy slicing either.
              if (requiresSlicing &&
                  visibleLength >= sourceLength - GEOMETRY_TOLERANCE) {
                  break;
              }
              const candidate = {
                  levelIndex,
                  slices: runs.slice(0, sliceCount),
                  score: visibleLength / sourceLength -
                      EXTRA_SLICE_PENALTY * (sliceCount - 1),
              };
              if (isBetterSlicePlan(candidate, selected)) {
                  selected = candidate;
              }
          }
      }
      if (selected) {
          selected.slices.sort(compareByEventOrder);
      }
      return selected;
  }
  /** Whether a slice may legally sit at this level, per its own fence. */
  function isWithinLevelFence(slice, levelIndex, state) {
      const fence = computeLevelFence(slice, state);
      return levelIndex >= fence.min && levelIndex < fence.maxExclusive;
  }
  /** Comparison: score, then less fragmentation, then the shallower level. */
  function isBetterSlicePlan(candidate, current) {
      if (!current || candidate.score > current.score) {
          return true;
      }
      if (candidate.score < current.score) {
          return false;
      }
      if (candidate.slices.length !== current.slices.length) {
          return candidate.slices.length < current.slices.length;
      }
      return candidate.levelIndex < current.levelIndex;
  }
  /**
   * Merges strict lateral intersections into groups sorted by lateral start.
   * Each group's hidden slices are event-ordered.
   */
  function groupLaterallyIntersecting(hiddenSlices) {
      const groups = [];
      for (const slice of hiddenSlices) {
          addHiddenSliceToGroups(groups, slice);
      }
      return finalizeHiddenGroups(groups);
  }
  /**
   * Adds one hidden slice to its strict-intersection component and returns only
   * the newly covered spans. Exactly adjacent groups deliberately stay separate
   * because each group corresponds to one independently rendered more link.
   * The group list remains sorted by lateral start.
   */
  function addHiddenSliceToGroups(groups, slice) {
      const newSpans = subtractCoveredSpans(slice, groups);
      const untouchedGroups = [];
      const mergedSlices = [slice];
      let start = slice.start;
      let end = slice.end;
      for (const group of groups) {
          if (intersectSpans(group, slice)) {
              mergedSlices.push(...group.hiddenSlices);
              start = Math.min(start, group.start);
              end = Math.max(end, group.end);
          }
          else {
              untouchedGroups.push(group);
          }
      }
      mergedSlices.sort(compareByEventOrder);
      insertLaterally(untouchedGroups, {
          start,
          end,
          hiddenSlices: mergedSlices,
      });
      groups.splice(0, groups.length, ...untouchedGroups);
      return newSpans;
  }
  /**
   * Compiles internal accumulator groups for components: one entry per hidden
   * source event, in event order, spanning that source's fragment hull.
   */
  function finalizeHiddenGroups(groups) {
      return groups.map((group) => {
          const hiddenSlices = mergeAdjacentSlices(group.hiddenSlices);
          return {
              key: getSliceKey(hiddenSlices[0]),
              start: group.start,
              end: group.end,
              hiddenSlices,
          };
      });
  }
  /* ========================================================================
   * Slice utilities
   * ===================================================================== */
  /**
   * Identifies a whole or partial slice derived from a source seg. Partial keys
   * deliberately omit the lateral end so a fragment re-cut at the same start
   * keeps its DOM wrapper. The re-cut fragment transiently reuses the previous
   * cut's measurement, which can mis-prune one pass; the structure still settles
   * because every fragment cut depends only on logical geometry — the same
   * wrapper just re-reports at its new width and the next pass corrects the
   * decision.
   */
  function getSliceKey(slice) {
      if (!isPartialSlice(slice)) {
          return slice.sourceSeg.key;
      }
      return `${slice.sourceSeg.key}:${slice.start}:slice`;
  }
  function isPartialSlice(slice) {
      return slice.start !== slice.sourceSeg.start ||
          slice.end !== slice.sourceSeg.end;
  }
  function compareByEventOrder(a, b) {
      return a.sourceSeg.orderIndex - b.sourceSeg.orderIndex ||
          a.start - b.start ||
          b.end - a.end; // longer events first
  }
  function sortByEventOrder(slices) {
      return [...slices].sort(compareByEventOrder);
  }
  /** Orders by axis start, then resolved event order. */
  function compareByAxisOrder(a, b) {
      return a.start - b.start ||
          a.sourceSeg.orderIndex - b.sourceSeg.orderIndex;
  }
  function sortByAxisOrder(items) {
      return [...items].sort(compareByAxisOrder);
  }
  /**
   * Collapses same-source runs of an event-ordered slice list into one slice
   * per run spanning the run's lateral hull. The hull can bridge territory
   * where the source is actually visible; consumers derive start/end
   * continuity from the outermost hidden edges, not exact hidden coverage.
   */
  function mergeAdjacentSlices(slices) {
      const merged = [];
      for (const slice of slices) {
          const previous = merged[merged.length - 1];
          if (previous && previous.sourceSeg === slice.sourceSeg) {
              merged[merged.length - 1] = createNarrowerSlice(createWholeSlice(previous.sourceSeg), previous.start, Math.max(previous.end, slice.end));
          }
          else {
              merged.push(slice);
          }
      }
      return merged;
  }
  /**
   * Removes covered spans from a slice, returning identity-preserving
   * remainders. Like `subtractCoveredSpans`, the covered spans must be sorted
   * by start and pairwise non-overlapping — every caller already holds them
   * that way (plan slices, union blockers, a single span).
   */
  function subtractSpansFromSlice(slice, covered) {
      return subtractCoveredSpans(slice, covered).map((span) => createNarrowerSlice(slice, span.start, span.end));
  }
  /** Finds the strict intersection while retaining source identity. */
  function intersectSlice(slice, barrier) {
      const intersection = intersectSpans(slice, barrier);
      return intersection
          ? createNarrowerSlice(slice, intersection.start, intersection.end)
          : null;
  }
  function createWholeSlice(sourceSeg) {
      return {
          sourceSeg,
          start: sourceSeg.start,
          end: sourceSeg.end,
          isStart: sourceSeg.isStart,
          isEnd: sourceSeg.isEnd,
      };
  }
  function createNarrowerSlice(parent, start, end) {
      return {
          sourceSeg: parent.sourceSeg,
          start,
          end,
          isStart: parent.isStart && start === parent.start,
          isEnd: parent.isEnd && end === parent.end,
      };
  }

  const DEFAULT_UNMEASURED_EVENT_AREA_HEIGHT = 150;
  /** Initial DOM candidate frontier, before any measurement can widen it. */
  const DEFAULT_LEVEL_CAPACITY = estimateLevelCapacity(DEFAULT_UNMEASURED_EVENT_AREA_HEIGHT, DEFAULT_UNMEASURED_EVENT_THICKNESS);
  /** Converts sorted production ranges into the shared source vocabulary. */
  function buildDayGridSegSources(eventOrderedSegs) {
      return eventOrderedSegs.map((seg, orderIndex) => ({
          ...seg,
          key: getDayGridSegKey(seg),
          orderIndex,
      }));
  }
  /**
   * Builds an immediately renderable kernel layout for unlimited and numeric
   * DayGrid modes. Boolean-auto uses the pixel-limited adapter below.
   */
  function buildDayGridLevelPlacements(eventOrderedSegs, maxLevels, moreLinkLevelTax, orderStrict, eventSlicing, columnCount, sliceHeights) {
      const sourceSegs = buildDayGridSegSources(eventOrderedSegs);
      const layout = buildLevelLimitedLayout(sourceSegs, orderStrict, eventSlicing, maxLevels, moreLinkLevelTax, sliceHeights);
      return buildDayGridPlacementLayout(sourceSegs, layout, sliceHeights, columnCount);
  }
  /** Builds the boolean-auto DayGrid route with a real pixel ceiling. */
  function buildDayGridPixelPlacements(eventOrderedSegs, orderStrict, eventSlicing, columnCount, canvasHeight, moreLinkHeight, levelCapacity, sliceHeights) {
      const sourceSegs = buildDayGridSegSources(eventOrderedSegs);
      const layout = buildPixelLimitedLayout(sourceSegs, orderStrict, eventSlicing, sliceHeights, canvasHeight, levelCapacity, moreLinkHeight);
      return buildDayGridPlacementLayout(sourceSegs, layout, sliceHeights, columnCount);
  }
  /** Projects ordered sources and event-ordered hidden slices into one cell. */
  function buildDayGridPopoverSegs(eventOrderedSegs, hiddenSlices, column) {
      return {
          segs: flatMapArray(eventOrderedSegs, (source) => cutSegToColumn(source, column) ?? []),
          hiddenSegs: flatMapArray(hiddenSlices, (slice) => cutSegToColumn(slice.sourceSeg, column, slice) ?? []),
      };
  }
  /**
   * Projects one complete source onto a column when its relevant span intersects.
   *
   * The optional span lets a hidden slice control membership while real event
   * boundaries still control whether the projected entry reports "continues."
   */
  function cutSegToColumn(source, column, intersectionSpan = source) {
      if (intersectionSpan.start >= column + 1 ||
          column >= intersectionSpan.end)
          return null;
      const { key, orderIndex, ...seg } = source;
      return {
          ...seg,
          start: column,
          end: column + 1,
          isStart: seg.isStart && source.start === column,
          isEnd: seg.isEnd && source.end - 1 === column,
      };
  }
  /**
   * Resolves which measured route a row takes from the two max options.
   *
   * This is the single definition of production's option precedence: a boolean
   * `true` on either option means auto, and only then does a number on either
   * one apply, `dayMaxEvents` first.
   */
  function resolveDayGridPlacementMode(dayMaxEvents, dayMaxEventRows) {
      if (dayMaxEvents === true || dayMaxEventRows === true) {
          return 'auto';
      }
      if (typeof dayMaxEvents === 'number') {
          return 'maxEvents';
      }
      if (typeof dayMaxEventRows === 'number') {
          return 'maxEventRows';
      }
      return 'unlimited';
  }
  /**
   * Computes the dimensionless DOM frontier from an already-resolved mode,
   * without applying more-link tax. Numeric limits own their explicit cap;
   * unlimited rows mount all sources; boolean-auto rows consume their row-local
   * observed frontier.
   */
  function computeDayGridDomCandidateMaxLevels(mode, dayMaxEvents, dayMaxEventRows, maxDomLevels) {
      switch (mode) {
          case 'auto': return maxDomLevels;
          case 'maxEvents': return dayMaxEvents;
          case 'maxEventRows': return dayMaxEventRows;
          default: return Infinity;
      }
  }
  /**
   * Logical levels an active more link charges its column. Only `dayMaxEventRows`
   * counts the link as one of its rows.
   */
  function computeDayGridMoreLinkLevelTax(mode) {
      return mode === 'maxEventRows' ? 1 : 0;
  }
  function buildDayGridPlacementLayout(sourceSegs, layout, sliceHeights, columnCount) {
      const { hiddenSlices, renderSlices, sliceCoords, } = layout;
      const eventOrderedHiddenSlices = sortByEventOrder(hiddenSlices);
      const slicesByStart = federateSlicesByStart(renderSlices, columnCount);
      const columns = Array.from({ length: columnCount }, (_, column) => ({
          // Freshly built per column by federateSlicesByStart; owned outright.
          renderSlices: slicesByStart[column],
          contentHeight: 0,
          ...buildDayGridPopoverSegs(sourceSegs, eventOrderedHiddenSlices, column),
      }));
      // A mounted slice is visible exactly when it has a coordinate; a coordinate
      // in turn guarantees a measurement.
      for (const slice of renderSlices) {
          const key = getSliceKey(slice);
          const sliceTop = sliceCoords.get(key);
          if (sliceTop === undefined) {
              continue;
          }
          const sliceBottom = sliceTop + sliceHeights.get(key);
          for (let column = slice.start; column < slice.end; column += 1) {
              columns[column].contentHeight = Math.max(columns[column].contentHeight, sliceBottom);
          }
      }
      return {
          columns,
          sliceCoords,
      };
  }
  function federateSlicesByStart(renderSlices, columnCount) {
      const slicesByStart = Array.from({ length: columnCount }, () => []);
      for (const slice of renderSlices) {
          slicesByStart[slice.start].push(slice);
      }
      for (const slices of slicesByStart) {
          slices.sort(compareByEventOrder);
      }
      return slicesByStart;
  }
  function estimateLevelCapacity(eventAreaHeight, eventHeight) {
      return Math.max(1, Math.ceil(eventAreaHeight / eventHeight));
  }

  /** High but finite safety cap for event levels in either print view. */
  const DEFAULT_PRINT_MAX_LEVELS = 200;
  function planPrintDomCandidates(eventOrderedSegs, eventOrderStrict, eventSlicing) {
      const { segLevels, excludedSegs } = buildSegLevels(eventOrderedSegs, eventOrderStrict, DEFAULT_PRINT_MAX_LEVELS);
      const placement = placeExtraSlicesInLevels(convertSegLevelsToWholeSlices(segLevels), convertSegsToWholeSlices(excludedSegs), eventOrderStrict, eventSlicing, 0);
      return {
          sliceLevels: placement.sliceLevels,
          hiddenSlices: placement.hiddenSlices,
      };
  }
  /**
   * Projects dimensionless levels into independently page-breakable bands.
   *
   * The level entries may carry unit-thickness planning coordinates, but those
   * coordinates have no print meaning. Every print slice begins at level
   * coordinate zero in its own band, whose thickness is the largest current
   * slice-wrapper measurement. Missing measurements use the supplied fallback.
   * Empty or sparse levels do not create empty DOM bands. The key resolver lets
   * adapters retain their wrapper-level measurement identity.
   */
  function buildPrintEventBands(levels, printEventThicknesses, getPrintEventKey = (slice) => slice.sourceSeg.key, defaultPrintEventThickness = DEFAULT_UNMEASURED_EVENT_THICKNESS) {
      const bands = [];
      for (let levelIndex = 0; levelIndex < levels.length; levelIndex++) {
          const entries = levels[levelIndex];
          if (!entries?.length)
              continue;
          let thickness = 0;
          const slices = entries.map((slice) => {
              thickness = Math.max(thickness, printEventThicknesses.get(getPrintEventKey(slice)) ??
                  defaultPrintEventThickness);
              return slice;
          });
          bands.push({
              levelIndex,
              slices,
              thickness,
          });
      }
      return bands;
  }
  /** Builds Timeline's one final print more-link band when hidden groups exist. */
  function buildPrintMoreLinkBand(hiddenGroups, printMoreLinkHeights) {
      if (!hiddenGroups.length) {
          return null;
      }
      // Group members arrive event-ordered, with the first member defining the key.
      return {
          moreLinkGroups: hiddenGroups,
          thickness: Math.max(...hiddenGroups.map((group) => printMoreLinkHeights.get(group.key) ??
              DEFAULT_UNMEASURED_MORE_LINK_THICKNESS)),
      };
  }

  /** Plans one print row from its complete, resolved-order source list. */
  function buildDayGridPrintPlan(eventOrderedSegs, orderStrict, eventSlicing, columnCount) {
      const sourceSegs = buildDayGridSegSources(eventOrderedSegs);
      const candidatePlan = planPrintDomCandidates(sourceSegs, orderStrict, eventSlicing);
      return {
          ...candidatePlan,
          hiddenSlices: sortByEventOrder(candidatePlan.hiddenSlices),
          sourceSegs,
          columnCount,
      };
  }
  /** Transposes row-wide print bands into one aligned slot sequence per cell. */
  function buildDayGridPrintColumns(plan, printSegHeights) {
      const columns = Array.from({ length: plan.columnCount }, () => []);
      for (const band of buildPrintEventBands(plan.sliceLevels, printSegHeights, getDayGridPrintSliceKey)) {
          const slicesByColumn = Array(plan.columnCount).fill(null);
          for (const slice of band.slices) {
              slicesByColumn[slice.start] = slice;
          }
          for (let column = 0; column < plan.columnCount; column++) {
              columns[column].push({
                  levelIndex: band.levelIndex,
                  thickness: band.thickness,
                  slice: slicesByColumn[column],
              });
          }
      }
      return columns;
  }
  /** Stable identity for one print wrapper when a source is split laterally. */
  function getDayGridPrintSliceKey(slice) {
      return `${slice.sourceSeg.key}:${slice.start}:${slice.end}`;
  }

  const DEFAULT_WEEK_NUM_FORMAT$1 = createFormatter({ week: 'narrow' });
  class DayGridRow extends BaseComponent {
      constructor() {
          super(...arguments);
          // ref
          this.headerHeightRefMap = new RefMap(() => {
              afterSize(this.handleSegPositioning);
          });
          this.mainHeightRefMap = new RefMap(() => {
              // Recorded in every screen mode so a row that becomes liquid already knows its
              // ceiling, but only a liquid row's placement depends on it.
              const fgLiquidHeight = this.props.dayMaxEvents === true || this.props.dayMaxEventRows === true;
              if (fgLiquidHeight) {
                  afterSize(this.handleSegPositioning);
              }
          });
          // Every screen slice (whole or partial) reports its occupied height here.
          this.sliceHeightRefMap = new RefMap(() => {
              afterSize(this.handleSegPositioning);
          });
          // print-only (band thickness is row-wide while slots render per-cell, so
          // this state must live here; see also buildPrintPlan, renderPrintBandSlots,
          // handlePrintSegHeights, and the reset in componentDidUpdate)
          this.handlePrintSegHeightChange = () => {
              afterSize(this.handlePrintSegHeights);
          };
          this.printSegHeightRefMap = new RefMap(this.handlePrintSegHeightChange);
          // memo
          this.buildWeekNumberRenderProps = memoize(buildWeekNumberRenderProps);
          this.buildPrintPlan = memoize(buildDayGridPrintPlan);
          this.sortEventSegs = memoize(sortEventSegs);
          this.levelCapacity = DEFAULT_LEVEL_CAPACITY;
          this.handleRootEl = (rootEl) => {
              this.disconnectHeight?.();
              this.disconnectHeight = undefined;
              setRef(this.props.rootElRef, rootEl);
              if (rootEl) {
                  this.disconnectHeight = watchHeight(rootEl, (contentHeight) => {
                      setRef(this.props.heightRef, contentHeight);
                  });
              }
          };
          this.handleSegPositioning = () => {
              if (this._isUnmounting || this.props.forPrint)
                  return;
              this.updateAutoPlacementRatchets();
              this.forceUpdate();
          };
          this.handlePrintSegHeights = () => {
              if (this._isUnmounting || !this.props.forPrint)
                  return;
              this.forceUpdate();
          };
      }
      render() {
          const { props, context, headerHeightRefMap, mainHeightRefMap } = this;
          const { cells, tableMode } = props;
          const { options } = context;
          const weekDateMarker = props.cells[0].date;
          const fgEventSegs = this.sortEventSegs(props.fgEventSegs, options.eventOrder);
          const screenFgLiquidHeight = props.dayMaxEvents === true || props.dayMaxEventRows === true;
          let printPlan = null;
          let printColumns = null;
          let screenColumns = null;
          let screenSliceCoords = new Map();
          let screenMainOffsetsByCol = [];
          let screenHeightsByCol = [];
          if (props.forPrint) {
              printPlan = this.buildPrintPlan(fgEventSegs, options.eventOrderStrict, options.eventSlicing, cells.length);
              printColumns = buildDayGridPrintColumns(printPlan, this.printSegHeightRefMap.current);
          }
          else {
              const placementMode = resolveDayGridPlacementMode(props.dayMaxEvents, props.dayMaxEventRows);
              const [maxMainTop, minMainHeight] = this.computeFgDims();
              const screenLayout = placementMode === 'auto'
                  ? buildDayGridPixelPlacements(fgEventSegs, options.eventOrderStrict, options.eventSlicing, cells.length, minMainHeight, props.moreLinkHeight, this.levelCapacity, this.sliceHeightRefMap.current)
                  : buildDayGridLevelPlacements(fgEventSegs, computeDayGridDomCandidateMaxLevels(placementMode, props.dayMaxEvents, props.dayMaxEventRows, Infinity), computeDayGridMoreLinkLevelTax(placementMode), options.eventOrderStrict, options.eventSlicing, cells.length, this.sliceHeightRefMap.current);
              screenColumns = screenLayout.columns;
              screenSliceCoords = screenLayout.sliceCoords;
              if (maxMainTop != null) {
                  for (let col = 0; col < cells.length; col++) {
                      const cellHeaderHeight = headerHeightRefMap.current.get(cells[col].key);
                      const mainOffset = cellHeaderHeight != null
                          ? maxMainTop - cellHeaderHeight
                          : undefined;
                      screenMainOffsetsByCol.push(mainOffset);
                      screenHeightsByCol.push(mainOffset != null
                          ? screenColumns[col].contentHeight + mainOffset
                          : undefined);
                  }
              }
          }
          const highlightSegs = this.getHighlightSegs();
          const hasNavLink = options.navLinks;
          const fullWeekStr = buildDateStr(context, weekDateMarker, 'week');
          const weekNumberRenderProps = this.buildWeekNumberRenderProps(weekDateMarker, context, props.cellIsNarrow, hasNavLink);
          const fillsByCol = cells.map(() => []);
          // Table mode gives this theme-positioned node a row-wide canvas hosted by the first cell.
          const weekNumberNode = (props.showWeekNumbers && !props.cellIsMicro) ? (u$1(ContentContainer, { tag: "div", attrs: {
                  ...(hasNavLink
                      ? buildNavLinkAttrs(context, weekDateMarker, 'week', fullWeekStr, /* isTabbable = */ false)
                      : {}),
                  'role': undefined, // HACK: a 'link' role can't be child of a 'row' role
                  'aria-hidden': true, // HACK: never part of a11y tree because row already has label and role not allowed
              }, className: DAY_GRID_EVENT_Z_CLASS, renderProps: weekNumberRenderProps, generatorName: "inlineWeekNumberContent", customGenerator: options.inlineWeekNumberContent, defaultGenerator: renderText$1, classNameGenerator: options.inlineWeekNumberClass, didMount: options.inlineWeekNumberDidMount, willUnmount: options.inlineWeekNumberWillUnmount })) : null;
          if (tableMode && weekNumberNode) {
              fillsByCol[0].push(u$1("div", { className: joinClassNames(classNames.fillY, classNames.start0, classNames.pointerEventsNone), style: {
                      width: this.computeSpanWidth(0, cells.length),
                  }, children: weekNumberNode }, "week-number"));
          }
          this.appendFillSegs(fillsByCol, props.businessHourSegs, 'non-business', DAY_GRID_NON_BUSINESS_Z_CLASS);
          this.appendFillSegs(fillsByCol, props.bgEventSegs, 'bg-event', DAY_GRID_BG_EVENT_Z_CLASS);
          this.appendFillSegs(fillsByCol, highlightSegs, 'highlight', DAY_GRID_HIGHLIGHT_Z_CLASS);
          const RowTag = tableMode ? 'tr' : 'div';
          return (u$1(RowTag, { role: props.role /* !!! */, "aria-label": props.role === 'row' // HACK
                  ? fullWeekStr
                  : undefined // can't have label on non-role div
              , className: joinClassNames(options.dayRowClass, props.className, tableMode && classNames.borderless, !tableMode && classNames.flexRow, !tableMode && classNames.rel, // origin for the inline week number
              !tableMode && classNames.borderlessX, !tableMode && classNames.borderlessTop, (!tableMode && !props.borderBottom) && classNames.borderlessBottom, classNames.isolate), style: {
                  flexBasis: tableMode ? undefined : props.basis,
              }, ref: this.handleRootEl, children: [!tableMode && weekNumberNode, props.cells.map((cell, col) => {
                      const printPopover = printPlan
                          ? buildDayGridPopoverSegs(printPlan.sourceSegs, printPlan.hiddenSlices, col)
                          : null;
                      let fg;
                      if (printPlan) {
                          fg = this.renderPrintBandSlots(printColumns[col]);
                      }
                      else {
                          fg = [
                              ...this.renderLevelFgSegs(screenMainOffsetsByCol[col], screenColumns[col].renderSlices, screenSliceCoords),
                              ...this.renderMirrorFgSegs(col, screenMainOffsetsByCol[col], screenSliceCoords),
                          ];
                      }
                      return (u$1(DayGridCell, { dateProfile: props.dateProfile, todayRange: props.todayRange, date: cell.date, isMajor: cell.isMajor, isDisabled: cell.isDisabled, showDayNumber: props.showDayNumbers, isNarrow: props.cellIsNarrow, isMicro: props.cellIsMicro, borderStart: Boolean(col), borderBottom: props.borderBottom, tableMode: tableMode, 
                          // content
                          fills: fillsByCol[col], segs: printPopover ? printPopover.segs : screenColumns[col].segs, hiddenSegs: printPopover ? printPopover.hiddenSegs : screenColumns[col].hiddenSegs, fgLiquidHeight: printPlan ? false : screenFgLiquidHeight, fg: fg, eventDrag: printPlan ? null : props.eventDrag, eventResize: printPlan ? null : props.eventResize, eventSelection: props.eventSelection, 
                          // render hooks
                          renderProps: cell.renderProps, dateSpanProps: cell.dateSpanProps, attrs: cell.attrs, className: cell.className, 
                          // dimensions
                          fgHeight: printPlan ? undefined : screenHeightsByCol[col], width: props.colWidth, 
                          // refs
                          headerHeightRef: printPlan ? undefined : headerHeightRefMap.createRef(cell.key), mainHeightRef: printPlan ? undefined : mainHeightRefMap.createRef(cell.key) }, cell.key));
                  })] }));
      }
      /** Mirrors align with kernel coordinates but bypass admission and measurement. */
      renderMirrorFgSegs(col, mainOffset, sliceCoords) {
          const { props } = this;
          const { eventSelection } = props;
          const nodes = [];
          for (const seg of this.getMirrorSegs()) {
              if (seg.start !== col) {
                  continue;
              }
              const key = getDayGridSegKey(seg);
              const { eventRange } = seg;
              const { instanceId } = eventRange.instance;
              const top = mainOffset != null
                  ? mainOffset + (sliceCoords.get(key) ?? 0)
                  : undefined;
              const isDragging = Boolean(props.eventDrag && props.eventDrag.affectedInstances[instanceId]);
              const isResizing = Boolean(props.eventResize && props.eventResize.affectedInstances[instanceId]);
              const isSelected = instanceId === eventSelection;
              nodes.push(u$1(MeasuredHeightHarness, { className: joinClassNames(classNames.abs, classNames.start0, DAY_GRID_INTERACTION_Z_CLASS), style: {
                      top,
                      width: this.computeSpanWidth(seg.start, seg.end),
                  }, heightRef: null, children: this.renderEventContent(seg, eventRange, {
                      isDragging,
                      isResizing,
                      isMirror: true,
                      isSelected,
                  }) }, `mirror:${key}`));
          }
          return nodes;
      }
      /** Renders every kernel slice with its own measurement ref. */
      renderLevelFgSegs(mainOffset, slices, sliceCoords) {
          const { props } = this;
          const { eventSelection } = props;
          const nodes = [];
          for (const slice of slices) {
              const key = getSliceKey(slice);
              const sliceTop = sliceCoords.get(key);
              const { eventRange } = slice.sourceSeg;
              const { instanceId } = eventRange.instance;
              const top = mainOffset != null && sliceTop != null
                  ? mainOffset + sliceTop
                  : undefined;
              const isDragging = Boolean(props.eventDrag && props.eventDrag.affectedInstances[instanceId]);
              const isResizing = Boolean(props.eventResize && props.eventResize.affectedInstances[instanceId]);
              const isInvisible = isDragging || isResizing || top == null;
              const isSelected = instanceId === eventSelection;
              nodes.push(u$1(MeasuredHeightHarness, { className: joinClassNames(classNames.abs, classNames.start0, isSelected ? DAY_GRID_INTERACTION_Z_CLASS : DAY_GRID_EVENT_Z_CLASS), style: {
                      visibility: isInvisible ? 'hidden' : undefined,
                      top,
                      width: this.computeSpanWidth(slice.start, slice.end),
                  }, heightRef: this.sliceHeightRefMap.createRef(key), children: this.renderEventContent(slice, eventRange, {
                      isDragging,
                      isResizing,
                      isSelected,
                  }) }, key));
          }
          return nodes;
      }
      /**
       * The inner event, identical on both placement routes. Only the wrapper
       * around it differs: the screen route positions it, print lets it sit at the
       * static top of its band slot.
      */
      renderEventContent(range, eventRange, interaction) {
          const { props } = this;
          const isListItem = hasListItemDisplay(range, eventRange);
          return (u$1(StandardEvent, { display: isListItem ? 'list-item' : 'row', eventRange: eventRange, isStart: range.isStart, isEnd: range.isEnd, isDragging: Boolean(interaction.isDragging), isResizing: Boolean(interaction.isResizing), isMirror: Boolean(interaction.isMirror), isSelected: Boolean(interaction.isSelected), isNarrow: props.cellIsNarrow, defaultTimeFormat: DEFAULT_TABLE_EVENT_TIME_FORMAT, defaultDisplayEventEnd: props.cells.length === 1, disableResizing: isListItem, forcedTimeText: props.cellIsMicro ? '' : undefined, ...getEventRangeMeta(eventRange, props.todayRange) }));
      }
      /** Renders aligned print slots with in-flow event wrappers that can paginate with their bands. */
      renderPrintBandSlots(slots) {
          const { printSegHeightRefMap } = this;
          return slots.map((slot) => {
              const { slice } = slot;
              let eventNode = null;
              if (slice) {
                  const sliceKey = getDayGridPrintSliceKey(slice);
                  eventNode = (u$1(MeasuredHeightHarness, { className: joinClassNames(classNames.rel, classNames.flowRoot, DAY_GRID_EVENT_Z_CLASS), style: {
                          width: this.computeSpanWidth(slice.start, slice.end),
                      }, heightRef: printSegHeightRefMap.createRef(sliceKey), children: this.renderEventContent(slice, slice.sourceSeg.eventRange, {}) }, sliceKey));
              }
              return (u$1("div", { className: classNames.breakInsideAvoid, style: { height: slot.thickness }, children: eventNode }, slot.levelIndex));
          });
      }
      computeSpanWidth(start, end) {
          const span = end - start;
          const percentWidth = `${span * 100}%`;
          // Flex cells have uniform inner widths, so spans must add crossed borders.
          // Fixed-table cells have uniform outer widths; the borderless first cell's inner
          // width already includes that space, so no border compensation is needed.
          const crossedBorderWidth = this.props.tableMode && start === 0
              ? 0
              : Math.max(0, span - 1) * COL_BORDER_WIDTH;
          return crossedBorderWidth
              ? `calc(${percentWidth} + ${crossedBorderWidth}px)`
              : percentWidth;
      }
      /** Places each fill in its first cell while allowing its wrapper to span subsequent cells. */
      appendFillSegs(fillsByCol, segs, fillType, zClassName) {
          const { props, context } = this;
          const { todayRange } = props;
          for (const seg of segs) {
              fillsByCol[seg.start].push(u$1("div", { className: joinClassNames(classNames.fillY, classNames.start0, zClassName), style: {
                      width: this.computeSpanWidth(seg.start, seg.end),
                  }, children: fillType === 'bg-event' ?
                      u$1(BgEvent, { eventRange: seg.eventRange, isStart: seg.isStart, isEnd: seg.isEnd, isNarrow: props.cellIsNarrow, isVertical: false, ...getEventRangeMeta(seg.eventRange, todayRange) }) : (renderFill(fillType, context.options)) }, `${fillType}:${buildEventRangeKey(seg.eventRange)}:${seg.start}:${seg.end}`));
          }
      }
      // Sizing
      // -----------------------------------------------------------------------------------------------
      componentDidMount() {
          this._isUnmounting = false;
      }
      componentDidUpdate(prevProps) {
          if (prevProps.forPrint && !this.props.forPrint) {
              this.printSegHeightRefMap = new RefMap(this.handlePrintSegHeightChange);
          }
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.disconnectHeight?.();
          setRef(this.props.heightRef, null);
      }
      computeFgDims() {
          const { cells } = this.props;
          const headerHeightMap = this.headerHeightRefMap.current;
          const mainHeightMap = this.mainHeightRefMap.current;
          let maxMainTop;
          let minMainBottom;
          let isComplete = true;
          for (const cell of cells) {
              if (cell.isDisabled) {
                  continue;
              }
              const mainTop = headerHeightMap.get(cell.key);
              const mainHeight = mainHeightMap.get(cell.key);
              if (mainTop == null || mainHeight == null) {
                  isComplete = false;
              }
              if (mainTop != null) {
                  if (maxMainTop === undefined || mainTop > maxMainTop) {
                      maxMainTop = mainTop;
                  }
                  if (mainHeight != null) {
                      const mainBottom = mainTop + mainHeight;
                      if (minMainBottom === undefined || mainBottom < minMainBottom) {
                          minMainBottom = mainBottom;
                      }
                  }
              }
          }
          return [
              maxMainTop,
              isComplete && minMainBottom != null && maxMainTop != null
                  ? minMainBottom - maxMainTop
                  : undefined,
          ];
      }
      /**
       * Grows the row-local DOM candidate frontier from one post-size snapshot.
       * This is the only monotone state auto placement needs: the engine itself
       * consumes exact measurements and never predicts a thickness.
       */
      updateAutoPlacementRatchets() {
          if (resolveDayGridPlacementMode(this.props.dayMaxEvents, this.props.dayMaxEventRows) !== 'auto')
              return;
          const [, canvasHeight] = this.computeFgDims();
          if (canvasHeight != null) {
              const smallestSliceHeight = Math.min(...this.sliceHeightRefMap.current.values());
              this.levelCapacity = Math.max(this.levelCapacity, estimateLevelCapacity(canvasHeight, smallestSliceHeight));
          }
      }
      // Internal Utils
      // -----------------------------------------------------------------------------------------------
      getMirrorSegs() {
          let { props } = this;
          if (props.eventResize && props.eventResize.segs.length) { // messy check
              return props.eventResize.segs;
          }
          return [];
      }
      getHighlightSegs() {
          let { props } = this;
          if (props.eventDrag && props.eventDrag.segs.length) { // messy check
              return props.eventDrag.segs;
          }
          if (props.eventResize && props.eventResize.segs.length) { // messy check
              return props.eventResize.segs;
          }
          return props.dateSelectionSegs;
      }
  }
  function buildWeekNumberRenderProps(weekDateMarker, context, isNarrow, hasNavLink) {
      const { dateEnv, options } = context;
      const weekNum = dateEnv.computeWeekNumber(weekDateMarker);
      const weekNumTextParts = dateEnv.formatToParts(weekDateMarker, options.weekNumberFormat || DEFAULT_WEEK_NUM_FORMAT$1);
      const weekNumText = joinDateTimeFormatParts(weekNumTextParts);
      const weekDateZoned = dateEnv.toDate(weekDateMarker);
      return {
          num: weekNum,
          text: weekNumText,
          textParts: weekNumTextParts,
          date: weekDateZoned,
          isNarrow,
          hasNavLink,
      };
  }

  class DaySeriesModel {
      constructor(range, dateProfileGenerator) {
          let date = range.start;
          let { end } = range;
          let entries = [];
          let dates = [];
          let dayIndex = -1;
          while (date < end) { // loop each day from start to end
              if (dateProfileGenerator.isHiddenDay(date)) {
                  entries.push({
                      kind: 'hidden',
                      previousIndex: dayIndex,
                      nextIndex: dayIndex + 1,
                  });
              }
              else {
                  dayIndex += 1;
                  entries.push({ kind: 'visible', index: dayIndex });
                  dates.push(date);
              }
              date = addDays(date, 1);
          }
          this.rangeStart = range.start;
          this.dates = dates;
          this.entries = entries;
          this.cnt = dates.length;
      }
      sliceRange(range) {
          let firstResult = this.getDateIndex(range.start);
          let lastResult = this.getDateIndex(addDays(range.end, -1));
          let firstIndex = getFirstVisibleIndex(firstResult);
          let lastIndex = getLastVisibleIndex(lastResult);
          let clippedFirstIndex = Math.max(0, firstIndex);
          let clippedLastIndex = Math.min(this.cnt - 1, lastIndex);
          if (clippedFirstIndex <= clippedLastIndex) {
              return {
                  start: clippedFirstIndex,
                  end: clippedLastIndex + 1, // make exclusive
                  isStart: firstResult.kind === 'visible' && firstIndex === clippedFirstIndex,
                  isEnd: lastResult.kind === 'visible' && lastIndex === clippedLastIndex,
              };
          }
          return null;
      }
      getDateIndex(date) {
          let dayOffset = Math.floor(diffDays(this.rangeStart, date));
          if (dayOffset < 0) {
              return { kind: 'before', index: -1 };
          }
          if (dayOffset >= this.entries.length) {
              return { kind: 'after', index: this.cnt };
          }
          return this.entries[dayOffset];
      }
  }
  function getFirstVisibleIndex(result) {
      return result.kind === 'hidden' ? result.nextIndex : result.index;
  }
  function getLastVisibleIndex(result) {
      return result.kind === 'hidden' ? result.previousIndex : result.index;
  }

  function buildDayTableModel(dateProfile, dateProfileGenerator, dateEnv) {
      const daySeries = new DaySeriesModel(dateProfile.renderRange, dateProfileGenerator);
      const breakOnWeeks = /year|month|week/.test(dateProfile.currentRangeUnit);
      const majorUnit = !breakOnWeeks && computeMajorUnit(dateProfile, dateEnv);
      // Exclude 'day': when cells are themselves days, all would match and the boundary
      // distinction is meaningless (unlike timeline slots which can be sub-day).
      return new DayTableModel(daySeries, breakOnWeeks, dateEnv, majorUnit !== 'day' ? majorUnit : undefined, dateProfile.activeRange);
  }
  function computeColWidth(colCount, colMinWidth, viewportWidth) {
      if (viewportWidth == null) {
          return [undefined, undefined];
      }
      const colTempWidth = viewportWidth / colCount;
      if (colTempWidth < colMinWidth) {
          return [colMinWidth * colCount, colMinWidth];
      }
      return [viewportWidth, undefined];
  }
  // Positioning
  // -------------------------------------------------------------------------------------------------
  /*
  TODO: handle hidden-days better. If current day is hidden day, scrolls to way bottom
  */
  function computeTopFromDate(date, cellRows, rowHeightMap) {
      let top = 0;
      for (const cells of cellRows) {
          const key = cells[0].key;
          const start = cells[0].date;
          const end = cells[cells.length - 1].date; // inclusive end
          if (date >= start && date <= end) {
              return top;
          }
          const rowHeight = rowHeightMap.get(key);
          if (rowHeight == null) {
              return; // denote unknown
          }
          top += rowHeight;
      }
      return top;
  }
  function computeColFromPosition(positionLeft, elWidth, colWidth, colCount, isRtl) {
      const realColWidth = colWidth != null ? colWidth : elWidth / colCount;
      const colFromLeft = Math.floor(positionLeft / realColWidth);
      const col = isRtl ? (colCount - colFromLeft - 1) : colFromLeft;
      const left = colFromLeft * realColWidth;
      const right = left + realColWidth;
      return { col, left, right };
  }
  function computeRowFromPosition(positionTop, cellRows, rowHeightMap) {
      let row = 0;
      let top = 0;
      let bottom = 0;
      for (const cells of cellRows) {
          const key = cells[0].key;
          top = bottom;
          bottom = top + rowHeightMap.get(key);
          if (positionTop < bottom) {
              break;
          }
          row++;
      }
      return { row, top, bottom };
  }
  // Hit Element
  // -------------------------------------------------------------------------------------------------
  function getRowEl(rootEl, row) {
      return rootEl.querySelectorAll('[role=row]')[row];
  }
  function getCellEl(rowEl, col) {
      return rowEl.querySelectorAll('[role=gridcell]')[col];
  }
  // Header Formatting
  // -------------------------------------------------------------------------------------------------
  const dayMicroWidth = 60;
  const dayHeaderMicroFormat = createFormatter({
      weekday: 'narrow'
  });
  function createDayHeaderFormatter(explicitFormat, datesRepDistinctDays, dateCnt) {
      return explicitFormat || computeFallbackHeaderFormat(datesRepDistinctDays, dateCnt);
  }
  // Computes a default column header formatting string if `colFormat` is not explicitly defined
  function computeFallbackHeaderFormat(datesRepDistinctDays, dayCnt) {
      // if more than one week row, or if there are a lot of columns with not much space,
      // put just the day numbers will be in each cell
      if (!datesRepDistinctDays) {
          return createFormatter({ weekday: 'short' }); // "Sat"
      }
      if (dayCnt > 1) {
          return createFormatter({
              weekday: 'short',
              weekdayJustify: 'start',
              day: 'numeric',
              omitCommas: true,
              omitTrailing: true,
          });
      }
      return createFormatter({
          weekday: 'long',
          weekdayJustify: 'start',
          day: 'numeric',
          omitCommas: true,
          omitTrailing: true,
      });
  }

  class DayGridRows extends DateComponent {
      constructor() {
          super(...arguments);
          this.state = {};
          // memo
          this.splitBusinessHourSegs = memoize(splitSegsByRow);
          this.splitBgEventSegs = memoize(splitAllDaySegsByRow);
          this.splitFgEventSegs = memoize(splitSegsByRow);
          this.splitDateSelectionSegs = memoize(splitSegsByRow);
          this.splitEventDrag = memoize(splitInteractionByRow);
          this.splitEventResize = memoize(splitInteractionByRow);
          this.rowHeightRefMap = new RefMap((height, key) => {
              // HACKy way of syncing RefMap results with prop
              const { rowHeightRefMap } = this.props;
              if (rowHeightRefMap) {
                  rowHeightRefMap.handleValue(height, key);
              }
          });
          this.handleMoreLinkEl = (el) => {
              this.disconnectMoreLinkHeight?.();
              this.disconnectMoreLinkHeight = undefined;
              if (el) {
                  this.disconnectMoreLinkHeight = watchHeight(el, (height) => {
                      if (this._isUnmounting)
                          return;
                      this.setState({ moreLinkHeight: height });
                  });
              }
          };
          this.handleRootEl = (rootEl) => {
              this.rootEl = rootEl;
              if (rootEl) {
                  this.context.registerInteractiveComponent(this, {
                      el: rootEl,
                      isHitComboAllowed: this.props.isHitComboAllowed,
                  });
              }
              else {
                  this.context.unregisterInteractiveComponent(this);
              }
          };
      }
      render() {
          let { props, state, context, rowHeightRefMap } = this;
          let { options } = context;
          let { cellRows, tableMode } = props;
          let rowCount = cellRows.length;
          // Will cause rows to not be reused across months
          let firstCellKey = cellRows[0]?.[0]?.key || '';
          let fgEventSegsByRow = this.splitFgEventSegs(props.fgEventSegs, rowCount);
          let bgEventSegsByRow = this.splitBgEventSegs(props.bgEventSegs, rowCount);
          let businessHourSegsByRow = this.splitBusinessHourSegs(props.businessHourSegs, rowCount);
          let dateSelectionSegsByRow = this.splitDateSelectionSegs(props.dateSelectionSegs, rowCount);
          let eventDragByRow = this.splitEventDrag(props.eventDrag, rowCount);
          let eventResizeByRow = this.splitEventResize(props.eventResize, rowCount);
          let isHeightAuto = getIsHeightAuto(options);
          let rowHeightsRedistribute = !props.forPrint && !isHeightAuto;
          let rowBasis = computeRowBasis(props.visibleWidth, rowCount, isHeightAuto, options);
          const needsMoreLinkProbe = !props.forPrint && resolveDayGridPlacementMode(props.dayMaxEvents, props.dayMaxEventRows) === 'auto';
          const RowsTag = tableMode ? 'tbody' : 'div';
          return (u$1(S, { children: [u$1(RowsTag, { role: "rowgroup", className: joinClassNames(props.className, 
                      // HACK for Safari. Can't do break-inside:avoid with flexbox items, likely b/c it's not standard:
                      // https://stackoverflow.com/a/60256345
                      !tableMode && !props.forPrint && classNames.flexCol), style: tableMode ? undefined : { width: props.width }, ref: this.handleRootEl, children: cellRows.map((cells, row) => (u$1(DayGridRow, { role: "row", dateProfile: props.dateProfile, todayRange: props.todayRange, cells: cells, cellIsNarrow: props.cellIsNarrow, cellIsMicro: props.cellIsMicro, showDayNumbers: rowCount > 1, showWeekNumbers: rowCount > 1 && options.weekNumbers, forPrint: props.forPrint, tableMode: tableMode, borderBottom: row < rowCount - 1, 
                          // if not auto-height, distribute height of container somewhat evently to rows
                          className: rowHeightsRedistribute ? classNames.grow : undefined, 
                          // content
                          fgEventSegs: fgEventSegsByRow[row], bgEventSegs: bgEventSegsByRow[row], businessHourSegs: businessHourSegsByRow[row], dateSelectionSegs: dateSelectionSegsByRow[row], eventSelection: props.eventSelection, eventDrag: eventDragByRow[row], eventResize: eventResizeByRow[row], dayMaxEvents: props.dayMaxEvents, dayMaxEventRows: props.dayMaxEventRows, 
                          // dimensions
                          colWidth: props.colWidth, basis: rowBasis, moreLinkHeight: state.moreLinkHeight, 
                          // refs
                          heightRef: rowHeightRefMap.createRef(cells[0].key) }, firstCellKey + ':' + cells[0].key))) }), needsMoreLinkProbe && (u$1(MoreLinkTrigger, { num: 1, display: 'row', isNarrow: props.cellIsNarrow, isMicro: props.cellIsMicro, elRef: this.handleMoreLinkEl, className: classNames.offscreen, attrs: {
                          'aria-hidden': true,
                          inert: '',
                      } }))] }));
      }
      componentDidMount() {
          this._isUnmounting = false;
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.disconnectMoreLinkHeight?.();
      }
      // Hit System
      // -----------------------------------------------------------------------------------------------
      queryHit(isRtl, positionLeft, positionTop, elWidth) {
          const { props } = this;
          const colCount = props.cellRows[0].length;
          const { col, left, right } = computeColFromPosition(positionLeft, elWidth, props.colWidth, colCount, isRtl);
          const { row, top, bottom } = computeRowFromPosition(positionTop, props.cellRows, this.rowHeightRefMap.current);
          const cell = props.cellRows[row][col];
          const cellStartDate = cell.date;
          const cellEndDate = addDays(cellStartDate, 1);
          return {
              dateProfile: props.dateProfile,
              dateSpan: {
                  range: {
                      start: cellStartDate,
                      end: cellEndDate,
                  },
                  allDay: true,
                  ...cell.dateSpanProps,
              },
              getDayEl: () => getCellEl(getRowEl(this.rootEl, row), col),
              rect: {
                  left,
                  right,
                  top,
                  bottom,
              },
              layer: 0,
          };
      }
  }
  // Utils
  // -------------------------------------------------------------------------------------------------
  function isSegAllDay(seg) {
      return seg.eventRange.def.allDay;
  }
  function splitAllDaySegsByRow(segs, rowCnt) {
      return splitSegsByRow(segs.filter(isSegAllDay), rowCnt);
  }
  /*
  Amount of height a row should consume prior to expanding
  We don't want to use min-height with flexbox because we leverage min-height:auto,
  which yields value based on natural height of events
  */
  function computeRowBasis(visibleWidth, // should INCLUDE any scrollbar width to avoid oscillation
  rowCount, isHeightAuto, options) {
      if (visibleWidth != null) {
          // ensure a consistent row min-height modelled after a month with 6 rows respecting aspectRatio
          // will result in same minHeight regardless of weekends, dayMinWidth, height:auto
          const rowBasis = visibleWidth / options.aspectRatio / 6;
          // don't give minHeight when single-month non-auto-height
          // TODO: better way to detect this with DateProfile?
          return (rowCount > 6 || isHeightAuto) ? rowBasis : 0;
      }
      return 0;
  }

  class DayGridHeaderCell extends BaseComponent {
      constructor() {
          super(...arguments);
          this.state = {};
          // memo
          this.buildDayHeaderText = memoize(buildDayHeaderText);
          this.handleInnerEl = (innerEl) => {
              if (this.disconnectSize) {
                  this.disconnectSize();
                  this.disconnectSize = undefined;
              }
              if (innerEl) {
                  this.disconnectSize = watchSize(innerEl, (width, height) => {
                      if (this._isUnmounting)
                          return;
                      setRef(this.props.innerHeightRef, height);
                      this.setState({ innerWidth: width });
                  });
              }
              else {
                  setRef(this.props.innerHeightRef, null);
              }
          };
      }
      render() {
          const { props, state, context } = this;
          const { renderConfig, dataConfig, tableMode } = props;
          const colSpan = dataConfig.colSpan || 1;
          const totalColWidth = props.colWidth != null
              ? props.colWidth * colSpan
              : undefined;
          const isLiquid = !tableMode && totalColWidth == null;
          /*
          A liquid cell that spans multiple columns can't use the .liquid class, which gives every
          cell an equal share regardless of colSpan. Instead, grow proportionally to the columns
          covered. Like the body cells, use a zero basis so borders remain within the distributed
          border-box width.
          */
          const isSpanning = isLiquid && colSpan > 1;
          const style = tableMode ? undefined : isSpanning ? {
              flexGrow: colSpan,
              flexBasis: 0,
              minWidth: 0,
          } : {
              width: totalColWidth,
          };
          // HACK
          const isDisabled = dataConfig.renderProps.isDisabled;
          const finalRenderProps = renderConfig.dayHeaderFormat
              ? this.buildDayHeaderRenderProps(dataConfig.renderProps, props.cellIsNarrow, props.rowLevel, props.cellIsMicro, dataConfig.dateMarker, renderConfig.dayHeaderFormat, Boolean(renderConfig.datesRepDistinctDays), context.dateEnv)
              : {
                  ...dataConfig.renderProps,
                  isNarrow: props.cellIsNarrow,
                  level: props.rowLevel,
              };
          /*
          TODO: DRY with TimelineHeaderCell
          */
          const alignInput = renderConfig.align;
          const align = // normalized string-enum value
           typeof alignInput === 'function'
              ? alignInput({ level: props.rowLevel, inPopover: dataConfig.renderProps.inPopover, isNarrow: props.cellIsNarrow })
              : alignInput;
          const stickyInput = renderConfig.sticky;
          const isSticky = !tableMode &&
              props.rowLevel > 0 &&
              stickyInput !== false && (
          // if center-aligned, and wants to be sticky, must be >75% viewport width,
          // to avoid looking awkwardly aligned
          align !== 'center' || (totalColWidth != null &&
              props.viewportWidth != null &&
              totalColWidth > props.viewportWidth * 0.75));
          let edgeCoord;
          if (isSticky) {
              if (align === 'center') {
                  if (state.innerWidth != null) {
                      edgeCoord = `calc(50% - ${state.innerWidth / 2}px)`;
                  }
              }
              else {
                  edgeCoord = (typeof stickyInput === 'number' ||
                      typeof stickyInput === 'string') ? stickyInput : 0;
              }
          }
          /*
          In screen mode, alignment belongs on the outer flex cell so the inner element
          remains shrink-wrapped for sticky positioning measurements. In table mode, the
          <th> must remain a table cell, so alignment moves to its full-width inner flex
          element. That width cannot support sticky positioning, which table mode disables.
          */
          const alignClassName = align === 'center' ? classNames.alignCenter :
              align === 'end' ? classNames.alignEnd :
                  classNames.alignStart;
          const CellTag = tableMode ? 'th' : 'div';
          return (u$1(ContentContainer, { tag: CellTag, attrs: {
                  role: 'columnheader',
                  'aria-colspan': dataConfig.colSpan,
                  colSpan: tableMode ? colSpan : undefined,
                  ...dataConfig.attrs,
              }, className: joinClassNames(dataConfig.className, classNames.noMargin, classNames.noPadding, !tableMode && classNames.flexCol, classNames.borderlessTop, classNames.borderlessEnd, !props.borderStart && classNames.borderlessStart, !(tableMode && props.borderBottom) && classNames.borderlessBottom, !tableMode && alignClassName, isLiquid && !isSpanning && classNames.liquid, !isSticky && classNames.crop), style: style, renderProps: finalRenderProps, generatorName: renderConfig.generatorName, customGenerator: renderConfig.customGenerator, defaultGenerator: renderText$1, classNameGenerator: 
              // don't use custom classNames if disabled
              // TODO: make DRY with DayCellContainer
              isDisabled ? undefined : renderConfig.classNameGenerator, didMount: renderConfig.didMount, willUnmount: renderConfig.willUnmount, children: (InnerContainer) => (u$1("div", { ref: this.handleInnerEl, className: joinClassNames(classNames.flexCol, classNames.noShrink, classNames.whiteSpaceNoWrap, tableMode && alignClassName, isSticky && classNames.sticky), style: {
                      left: edgeCoord,
                      right: edgeCoord,
                  }, children: u$1(InnerContainer, { tag: 'div', attrs: dataConfig.innerAttrs, className: generateClassName(renderConfig.innerClassNameGenerator, finalRenderProps) }) })) }));
      }
      componentDidMount() {
          this._isUnmounting = false;
      }
      componentWillUnmount() {
          this._isUnmounting = true;
      }
      buildDayHeaderRenderProps(renderProps, cellIsNarrow, rowLevel, cellIsMicro, dateMarker, dayHeaderFormat, datesRepDistinctDays, dateEnv) {
          const baseText = this.buildDayHeaderText(datesRepDistinctDays ? dateMarker : renderProps.date, dayHeaderFormat, datesRepDistinctDays, dateEnv);
          const textData = cellIsMicro
              ? this.buildDayHeaderText(dateMarker, dayHeaderMicroFormat, false, dateEnv)
              : baseText;
          return {
              ...renderProps,
              isNarrow: cellIsNarrow,
              level: rowLevel,
              text: textData.text,
              textParts: textData.textParts,
              weekdayText: cellIsMicro ? textData.text : baseText.weekdayText,
              dayNumberText: baseText.dayNumberText,
          };
      }
  }
  function buildDayHeaderText(date, formatter, includeDayNumber, dateEnv) {
      const textParts = dateEnv.formatToParts(date, formatter);
      return {
          text: joinDateTimeFormatParts(textParts),
          textParts,
          weekdayText: findWeekdayText(textParts),
          dayNumberText: includeDayNumber ? findDayNumberText(textParts) : '',
      };
  }

  class DayGridHeaderRow extends BaseComponent {
      constructor() {
          super(...arguments);
          // ref
          this.innerHeightRefMap = new RefMap(() => {
              afterSize(this.handleInnerHeights);
          });
          this.handleInnerHeights = () => {
              if (this._isUnmounting)
                  return;
              const innerHeightMap = this.innerHeightRefMap.current;
              let max = 0;
              for (const innerHeight of innerHeightMap.values()) {
                  max = Math.max(max, innerHeight);
              }
              if (this.currentInnerHeight !== max) {
                  this.currentInnerHeight = max;
                  setRef(this.props.innerHeightRef, max);
              }
          };
      }
      render() {
          const { props, context } = this;
          const { tableMode } = props;
          const { options } = context;
          const RowTag = tableMode ? 'tr' : 'div';
          return (u$1(RowTag, { role: props.role /* !!! */, "aria-rowindex": props.rowIndex != null ? 1 + props.rowIndex : undefined, className: joinClassNames(options.dayHeaderRowClass, props.className, tableMode && classNames.borderless, !tableMode && classNames.flexRow, !tableMode && classNames.contentBox, !tableMode && classNames.borderlessX, !tableMode && classNames.borderlessTop, (!tableMode && !props.borderBottom) && classNames.borderlessBottom), style: {
                  height: props.height,
              }, children: props.dataConfigs.map((dataConfig, cellI) => (u$1(DayGridHeaderCell, { renderConfig: props.renderConfig, dataConfig: dataConfig, borderStart: Boolean(cellI), colWidth: props.colWidth, viewportWidth: props.viewportWidth, innerHeightRef: this.innerHeightRefMap.createRef(dataConfig.key), cellIsNarrow: props.cellIsNarrow, cellIsMicro: props.cellIsMicro, rowLevel: props.rowLevel, tableMode: tableMode, borderBottom: props.borderBottom }, dataConfig.key))) }));
      }
      componentDidMount() {
          this._isUnmounting = false;
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.currentInnerHeight = undefined;
          setRef(this.props.innerHeightRef, null);
      }
  }

  class DayGridHeaderRows extends BaseComponent {
      render() {
          const { props } = this;
          const { headerTiers, tableMode } = props;
          return headerTiers.map((rowConfig, i) => (k$1(DayGridHeaderRow, { ...rowConfig, key: i, role: 'row', borderBottom: i < headerTiers.length - 1, colWidth: props.colWidth, viewportWidth: props.viewportWidth, cellIsNarrow: props.cellIsNarrow, cellIsMicro: props.cellIsMicro, rowLevel: headerTiers.length - i - 1, tableMode: tableMode })));
      }
  }

  class DayGridLayoutPrint extends BaseComponent {
      render() {
          const { props, context } = this;
          const { options } = context;
          const tableDisplayInfo = {
              borderlessX: props.borderlessX,
              borderlessTop: props.borderlessTop,
              borderlessBottom: props.borderlessBottom,
              multiMonthColumns: props.multiMonthColumns,
          };
          return (u$1("table", { role: "presentation", className: joinClassNames(generateClassName(options.tableClass, tableDisplayInfo), classNames.printTable), style: props.style, children: [u$1("colgroup", { children: props.cellRows[0].map((cell) => u$1("col", {}, cell.key)) }), props.showHeader && (u$1("thead", { ref: props.headerElRef, role: "rowgroup", className: generateClassName(options.tableHeaderClass, {
                          ...tableDisplayInfo,
                          isSticky: false,
                      }), children: [u$1(DayGridHeaderRows, { tableMode: true, headerTiers: props.headerTiers, cellIsNarrow: props.cellIsNarrow, cellIsMicro: props.cellIsMicro }), u$1("tr", { role: "presentation", children: u$1("th", { role: "presentation", colSpan: props.cellRows[0].length, className: joinClassNames(classNames.noPadding, generateClassName(options.dayHeaderDividerClass, {
                                      isSticky: false,
                                      multiMonthColumns: props.multiMonthColumns,
                                      options: { allDaySlot: Boolean(options.allDaySlot) },
                                  })) }) })] })), u$1(DayGridRows, { dateProfile: props.dateProfile, todayRange: props.todayRange, cellRows: props.cellRows, forPrint: true, tableMode: true, className: generateClassName(options.tableBodyClass, tableDisplayInfo), dayMaxEvents: undefined, dayMaxEventRows: props.dayMaxEventRows, fgEventSegs: props.fgEventSegs, bgEventSegs: props.bgEventSegs, businessHourSegs: props.businessHourSegs, dateSelectionSegs: [], eventDrag: null, eventResize: null, eventSelection: props.eventSelection, visibleWidth: props.visibleWidth, cellIsNarrow: props.cellIsNarrow, cellIsMicro: props.cellIsMicro, rowHeightRefMap: props.rowHeightRefMap })] }));
      }
  }

  /*
  Used only for screen rendering. Print places DayGridHeaderRows directly inside a table header.
  */
  class DayGridHeader extends BaseComponent {
      render() {
          const { props } = this;
          return (u$1("div", { role: 'rowgroup', className: joinClassNames(props.className, classNames.flexCol, props.width == null && classNames.liquid), style: {
                  width: props.width,
              }, children: u$1(DayGridHeaderRows, { headerTiers: props.headerTiers, colWidth: props.colWidth, viewportWidth: props.viewportWidth, cellIsNarrow: props.cellIsNarrow, cellIsMicro: props.cellIsMicro }) }));
      }
  }

  class DayGridLayoutNormal extends BaseComponent {
      constructor() {
          super(...arguments);
          this.state = {};
          this.handleScroller = (scroller) => {
              setRef(this.props.scrollerRef, scroller);
          };
          this.handleTotalWidth = (totalWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ totalWidth });
          };
          this.handleClientWidth = (clientWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ clientWidth });
          };
      }
      render() {
          const { props, state, context } = this;
          const { options } = context;
          const { borderlessX, borderlessTop, borderlessBottom } = computeViewBorderless(options);
          const { totalWidth, clientWidth } = state;
          let endScrollbarWidth = (totalWidth != null && clientWidth != null)
              ? totalWidth - clientWidth
              : undefined;
          // HACK when clientWidth does NOT include body-border, compared to totalWidth
          if (endScrollbarWidth < 3) {
              endScrollbarWidth = 0;
          }
          const verticalScrollbars = !props.forPrint && !getIsHeightAuto(options);
          const tableHeaderSticky = !props.forPrint && getTableHeaderSticky(options);
          const colCount = props.cellRows[0].length;
          const measuredColWidth = clientWidth != null ? clientWidth / colCount : undefined;
          const cellIsMicro = measuredColWidth != null && measuredColWidth <= dayMicroWidth;
          const cellIsNarrow = cellIsMicro || (measuredColWidth != null && measuredColWidth <= options.dayNarrowWidth);
          if (props.forPrint) {
              return (u$1(DayGridLayoutPrint, { dateProfile: props.dateProfile, todayRange: props.todayRange, cellRows: props.cellRows, headerTiers: props.headerTiers, showHeader: Boolean(options.dayHeaders), fgEventSegs: props.fgEventSegs, bgEventSegs: props.bgEventSegs, businessHourSegs: props.businessHourSegs, eventSelection: props.eventSelection, dayMaxEventRows: options.dayMaxEventRows, borderlessX: borderlessX, borderlessTop: borderlessTop, borderlessBottom: borderlessBottom, multiMonthColumns: 0, visibleWidth: totalWidth, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, rowHeightRefMap: props.rowHeightRefMap }));
          }
          return (u$1(S, { children: [options.dayHeaders && (u$1("div", { className: joinClassNames(generateClassName(options.tableHeaderClass, {
                          isSticky: tableHeaderSticky,
                          borderlessX,
                          borderlessTop,
                          borderlessBottom,
                          multiMonthColumns: 0,
                      }), classNames.flexCol, tableHeaderSticky && classNames.tableHeaderSticky), children: [u$1("div", { className: classNames.flexRow, children: [u$1(DayGridHeader, { headerTiers: props.headerTiers, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro }), Boolean(endScrollbarWidth) && (u$1("div", { className: joinClassNames(generateClassName(options.fillerClass, { inTableHeader: true }), classNames.borderlessY, classNames.borderlessEnd), style: { minWidth: endScrollbarWidth } }))] }), u$1("div", { className: generateClassName(options.dayHeaderDividerClass, {
                                  isSticky: tableHeaderSticky,
                                  multiMonthColumns: 0,
                                  options: { allDaySlot: Boolean(options.allDaySlot) },
                              }) })] })), u$1(Scroller, { vertical: verticalScrollbars, className: joinClassNames(generateClassName(options.tableBodyClass, {
                          borderlessX,
                          borderlessTop,
                          borderlessBottom,
                          multiMonthColumns: 0,
                      }), 
                      // HACK for Safari. Can't do break-inside:avoid with flexbox items, likely b/c it's not standard:
                      // https://stackoverflow.com/a/60256345
                      !props.forPrint && classNames.flexCol, verticalScrollbars && classNames.liquid), ref: this.handleScroller, clientWidthRef: this.handleClientWidth, children: u$1(DayGridRows, { dateProfile: props.dateProfile, todayRange: props.todayRange, cellRows: props.cellRows, forPrint: props.forPrint, isHitComboAllowed: props.isHitComboAllowed, className: classNames.grow, dayMaxEvents: props.forPrint ? undefined : options.dayMaxEvents, dayMaxEventRows: options.dayMaxEventRows, 
                          // content
                          fgEventSegs: props.fgEventSegs, bgEventSegs: props.bgEventSegs, businessHourSegs: props.businessHourSegs, dateSelectionSegs: props.dateSelectionSegs, eventDrag: props.eventDrag, eventResize: props.eventResize, eventSelection: props.eventSelection, 
                          // dimensions
                          visibleWidth: totalWidth, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, 
                          // refs
                          rowHeightRefMap: props.rowHeightRefMap }) }), u$1(Ruler, { widthRef: this.handleTotalWidth })] }));
      }
      componentDidMount() {
          this._isUnmounting = false;
      }
      componentWillUnmount() {
          this._isUnmounting = true;
      }
  }

  class FooterScrollbar extends BaseComponent {
      constructor() {
          super(...arguments);
          this.rootElRef = M$1();
      }
      render() {
          const { props } = this;
          // NOTE: we need a wrapper around the Scroller because if scrollbars appear/hide,
          // the outer dimensions change, but the inner dimensions do not. The Scroller's
          // dimension-watching, when used in ponyfill-mode, can't fire on border-box change, so we
          // workaround it by monitoring dimensions of a wrapper instead
          return (u$1("div", { ref: this.rootElRef, className: joinClassNames(classNames.footerScrollbar, props.isSticky && classNames.footerScrollbarSticky), children: u$1(Scroller, { horizontal: true, ref: props.scrollerRef, children: u$1("div", { style: { minWidth: props.canvasWidth } }) }) }));
      }
      componentDidMount() {
          this._isUnmounting = false;
          this.disconnectHeight = watchHeight(this.rootElRef.current, (height) => {
              if (this._isUnmounting)
                  return;
              setRef(this.props.scrollbarWidthRef, height);
          });
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.disconnectHeight();
          setRef(this.props.scrollbarWidthRef, null);
      }
  }

  class DayGridLayoutPannable extends BaseComponent {
      constructor() {
          super(...arguments);
          this.state = {};
          this.headerScrollerRef = M$1();
          this.bodyScrollerRef = M$1();
          this.footerScrollerRef = M$1();
          // Sizing
          // -----------------------------------------------------------------------------------------------
          this.handleTotalWidth = (totalWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ totalWidth });
          };
          this.handleClientWidth = (clientWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ clientWidth });
          };
      }
      render() {
          const { props, state, context } = this;
          const { options } = context;
          const { borderlessX, borderlessTop, borderlessBottom } = computeViewBorderless(options);
          const { totalWidth, clientWidth } = state;
          const endScrollbarWidth = (totalWidth != null && clientWidth != null)
              ? totalWidth - clientWidth
              : undefined;
          const verticalScrollbars = !props.forPrint && !getIsHeightAuto(options);
          const tableHeaderSticky = !props.forPrint && getTableHeaderSticky(options);
          const footerScrollbarSticky = !props.forPrint && getFooterScrollbarSticky(options);
          const colCount = props.cellRows[0].length;
          const [canvasWidth, appliedColWidth] = computeColWidth(colCount, props.dayMinWidth, clientWidth);
          const measuredColWidth = appliedColWidth ?? (clientWidth != null ? clientWidth / colCount : undefined);
          const cellIsMicro = measuredColWidth != null && measuredColWidth <= dayMicroWidth;
          const cellIsNarrow = cellIsMicro || (measuredColWidth != null && measuredColWidth <= options.dayNarrowWidth);
          if (props.forPrint) {
              return (u$1(DayGridLayoutPrint, { dateProfile: props.dateProfile, todayRange: props.todayRange, cellRows: props.cellRows, headerTiers: props.headerTiers, showHeader: Boolean(options.dayHeaders), fgEventSegs: props.fgEventSegs, bgEventSegs: props.bgEventSegs, businessHourSegs: props.businessHourSegs, eventSelection: props.eventSelection, dayMaxEventRows: options.dayMaxEventRows, borderlessX: borderlessX, borderlessTop: borderlessTop, borderlessBottom: borderlessBottom, multiMonthColumns: 0, visibleWidth: totalWidth, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, rowHeightRefMap: props.rowHeightRefMap }));
          }
          return (u$1(S, { children: [options.dayHeaders && (u$1("div", { className: joinClassNames(generateClassName(options.tableHeaderClass, {
                          isSticky: tableHeaderSticky,
                          borderlessX,
                          borderlessTop,
                          borderlessBottom,
                          multiMonthColumns: 0,
                      }), classNames.flexCol, tableHeaderSticky && classNames.tableHeaderSticky), children: [u$1(Scroller, { horizontal: true, hideScrollbars: true, className: classNames.flexRow, ref: this.headerScrollerRef, children: [u$1(DayGridHeader, { headerTiers: props.headerTiers, colWidth: appliedColWidth, viewportWidth: clientWidth, width: canvasWidth, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro }), Boolean(endScrollbarWidth) && (u$1("div", { className: joinClassNames(generateClassName(options.fillerClass, { inTableHeader: true }), classNames.borderlessY, classNames.borderlessEnd), style: { minWidth: endScrollbarWidth } }))] }), u$1("div", { className: generateClassName(options.dayHeaderDividerClass, {
                                  isSticky: tableHeaderSticky,
                                  multiMonthColumns: 0,
                                  options: { allDaySlot: Boolean(options.allDaySlot) },
                              }) })] })), u$1(Scroller, { vertical: verticalScrollbars, horizontal: true, hideScrollbars: footerScrollbarSticky ||
                          props.forPrint // prevents blank space in print-view on Safari
                      , className: joinClassNames(generateClassName(options.tableBodyClass, {
                          borderlessX,
                          borderlessTop,
                          borderlessBottom,
                          multiMonthColumns: 0,
                      }), 
                      // HACK for Safari. Can't do break-inside:avoid with flexbox items, likely b/c it's not standard:
                      // https://stackoverflow.com/a/60256345
                      !props.forPrint && classNames.flexCol, verticalScrollbars && classNames.liquid), ref: this.bodyScrollerRef, clientWidthRef: this.handleClientWidth, children: u$1(DayGridRows, { dateProfile: props.dateProfile, todayRange: props.todayRange, cellRows: props.cellRows, forPrint: props.forPrint, isHitComboAllowed: props.isHitComboAllowed, className: classNames.grow, dayMaxEvents: props.forPrint ? undefined : options.dayMaxEvents, dayMaxEventRows: options.dayMaxEventRows, 
                          // content
                          fgEventSegs: props.fgEventSegs, bgEventSegs: props.bgEventSegs, businessHourSegs: props.businessHourSegs, dateSelectionSegs: props.dateSelectionSegs, eventDrag: props.eventDrag, eventResize: props.eventResize, eventSelection: props.eventSelection, 
                          // dimensions
                          colWidth: appliedColWidth, width: canvasWidth, visibleWidth: totalWidth, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, 
                          // refs
                          rowHeightRefMap: props.rowHeightRefMap }) }), Boolean(footerScrollbarSticky) && (u$1(FooterScrollbar, { isSticky: true, canvasWidth: canvasWidth, scrollerRef: this.footerScrollerRef })), u$1(Ruler, { widthRef: this.handleTotalWidth })] }));
      }
      // Lifecycle
      // -----------------------------------------------------------------------------------------------
      componentDidMount() {
          this._isUnmounting = false;
          // scroller
          const ScrollerSyncer = getScrollerSyncerClass(this.context.pluginHooks);
          this.syncedScroller = new ScrollerSyncer(true); // horizontal=true
          setRef(this.props.scrollerRef, this.syncedScroller);
          this.updateSyncedScroller();
      }
      componentDidUpdate() {
          // scroller
          this.updateSyncedScroller();
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          // scroller
          this.syncedScroller.destroy();
      }
      // Scrolling
      // -----------------------------------------------------------------------------------------------
      updateSyncedScroller() {
          this.syncedScroller.handleChildren([
              this.headerScrollerRef.current,
              this.bodyScrollerRef.current,
              this.footerScrollerRef.current,
          ]);
      }
  }

  class DayGridLayout extends BaseComponent {
      constructor() {
          super(...arguments);
          // ref
          this.scrollerRef = M$1();
          this.rowHeightRefMap = new RefMap(() => {
              afterSize(this.updateScrollY);
          });
          this.scrollDate = null;
          this.updateScrollY = () => {
              if (this._isUnmounting)
                  return;
              const rowHeightMap = this.rowHeightRefMap.current;
              const scroller = this.scrollerRef.current;
              // Since updateScrollY is called by rowHeightRefMap, could be called with null during cleanup,
              // and the scroller might not exist
              if (scroller && this.scrollDate) {
                  let scrollTop = computeTopFromDate(this.scrollDate, this.props.cellRows, rowHeightMap);
                  if (scrollTop != null) {
                      if (scrollTop) {
                          scrollTop++; // clear top border
                      }
                      scroller.scrollTo({ y: scrollTop });
                  }
              }
          };
          this.handleScrollEnd = (isDevice) => {
              if (isDevice) {
                  this.scrollDate = null;
              }
          };
      }
      render() {
          const { props, context } = this;
          const { options } = context;
          const { borderlessX, borderlessTop, borderlessBottom } = computeViewBorderless(options);
          const dateSelectionSegs = props.forPrint ? [] : props.dateSelectionSegs;
          const eventDrag = props.forPrint ? null : props.eventDrag;
          const eventResize = props.forPrint ? null : props.eventResize;
          const commonLayoutProps = {
              ...props,
              dateSelectionSegs,
              eventDrag,
              eventResize,
              scrollerRef: this.scrollerRef,
              rowHeightRefMap: this.rowHeightRefMap,
          };
          return (u$1(ViewContainer, { viewSpec: context.viewSpec, attrs: {
                  role: 'grid',
                  'aria-rowcount': props.headerTiers.length + props.cellRows.length,
                  'aria-colcount': props.cellRows[0].length,
                  'aria-labelledby': props.labelId,
                  'aria-label': props.labelStr,
              }, className: joinClassNames(props.className, !props.forPrint && classNames.flexCol, !props.forPrint && generateClassName(options.tableClass, {
                  borderlessX,
                  borderlessTop,
                  borderlessBottom,
                  multiMonthColumns: 0,
              })), children: options.dayMinWidth ? (u$1(DayGridLayoutPannable, { ...commonLayoutProps, dayMinWidth: options.dayMinWidth })) : (u$1(DayGridLayoutNormal, { ...commonLayoutProps })) }));
      }
      // Lifecycle
      // -----------------------------------------------------------------------------------------------
      componentDidMount() {
          this._isUnmounting = false;
          if (!this.props.forPrint) {
              this.resetScroll();
              this.scrollerRef.current?.addScrollEndListener(this.handleScrollEnd);
          }
      }
      componentDidUpdate(prevProps) {
          if (prevProps.forPrint && !this.props.forPrint) {
              this.scrollerRef.current?.addScrollEndListener(this.handleScrollEnd);
              this.resetScroll();
          }
          if (prevProps.dateProfile !== this.props.dateProfile && this.context.options.scrollTimeReset) {
              this.resetScroll();
          }
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.scrollerRef.current?.removeScrollEndListener(this.handleScrollEnd);
      }
      // Scrolling
      // -----------------------------------------------------------------------------------------------
      resetScroll() {
          this.scrollDate = this.props.dateProfile.currentDate;
          this.updateScrollY();
          this.scrollerRef.current?.scrollTo({ x: 0 });
      }
  }

  function buildDayCols(dateProfile, dateProfileGenerator, dateEnv, slotRange, majorUnit = '') {
      return buildDayColsFromSeries(new DaySeriesModel(dateProfile.renderRange, dateProfileGenerator), dateEnv, {
          slotRange,
          majorUnit,
          activeRange: dateProfile.activeRange,
      });
  }
  function buildDayColsFromSeries(daySeries, dateEnv, config = {}) {
      const { slotRange, majorUnit = '', activeRange } = config;
      return daySeries.dates.map((date) => ({
          key: date.toISOString(),
          date,
          range: slotRange
              ? {
                  start: dateEnv.add(date, slotRange.slotMinTime),
                  end: dateEnv.add(date, slotRange.slotMaxTime),
              }
              : {
                  start: date,
                  end: addDays(date, 1),
              },
          isMajor: majorUnit ? isMajorUnit(date, majorUnit, dateEnv) : false,
          isDisabled: activeRange === null || (activeRange !== undefined && !rangeContainsMarker(activeRange, date)),
      }));
  }

  const EMPTY_EVENT_STORE = createEmptyEventStore(); // for purecomponents. TODO: keep elsewhere
  class Splitter {
      constructor() {
          this.getKeysForEventDefs = memoize(this._getKeysForEventDefs);
          this.splitDateSelection = memoize(this._splitDateSpan);
          this.splitEventStore = memoize(this._splitEventStore);
          this.splitIndividualUi = memoize(this._splitIndividualUi);
          this.splitEventDrag = memoize(this._splitInteraction);
          this.splitEventResize = memoize(this._splitInteraction);
          this.eventUiBuilders = {}; // TODO: typescript protection
      }
      splitProps(props) {
          let keyInfos = this.getKeyInfo(props);
          let defKeys = this.getKeysForEventDefs(props.eventStore);
          let dateSelections = this.splitDateSelection(props.dateSelection);
          let individualUi = this.splitIndividualUi(props.eventUiBases, defKeys); // the individual *bases*
          let eventStores = this.splitEventStore(props.eventStore, defKeys);
          let eventDrags = this.splitEventDrag(props.eventDrag);
          let eventResizes = this.splitEventResize(props.eventResize);
          let splitProps = {};
          this.eventUiBuilders = mapHash(keyInfos, (info, key) => this.eventUiBuilders[key] || memoize(buildEventUiForKey));
          for (let key in keyInfos) {
              let keyInfo = keyInfos[key];
              let eventStore = eventStores[key] || EMPTY_EVENT_STORE;
              let buildEventUi = this.eventUiBuilders[key];
              splitProps[key] = {
                  businessHours: keyInfo.businessHours || props.businessHours,
                  dateSelection: dateSelections[key] || null,
                  eventStore,
                  eventUiBases: buildEventUi(props.eventUiBases[''], keyInfo.ui, individualUi[key]),
                  eventDrag: eventDrags[key] || null,
                  eventResize: eventResizes[key] || null,
                  eventSelection: eventStore.instances[props.eventSelection] ? props.eventSelection : '',
              };
          }
          return splitProps;
      }
      _splitDateSpan(dateSpan) {
          let dateSpans = {};
          if (dateSpan) {
              let keys = this.getKeysForDateSpan(dateSpan);
              for (let key of keys) {
                  dateSpans[key] = dateSpan;
              }
          }
          return dateSpans;
      }
      _getKeysForEventDefs(eventStore) {
          return mapHash(eventStore.defs, (eventDef) => this.getKeysForEventDef(eventDef));
      }
      _splitEventStore(eventStore, defKeys) {
          let { defs, instances } = eventStore;
          let splitStores = {};
          for (let defId in defs) {
              for (let key of defKeys[defId]) {
                  if (!splitStores[key]) {
                      splitStores[key] = createEmptyEventStore();
                  }
                  splitStores[key].defs[defId] = defs[defId];
              }
          }
          for (let instanceId in instances) {
              let instance = instances[instanceId];
              for (let key of defKeys[instance.defId]) {
                  if (splitStores[key]) { // must have already been created
                      splitStores[key].instances[instanceId] = instance;
                  }
              }
          }
          return splitStores;
      }
      _splitIndividualUi(eventUiBases, defKeys) {
          let splitHashes = {};
          for (let defId in eventUiBases) {
              if (defId) { // not the '' key
                  for (let key of defKeys[defId]) {
                      if (!splitHashes[key]) {
                          splitHashes[key] = {};
                      }
                      splitHashes[key][defId] = eventUiBases[defId];
                  }
              }
          }
          return splitHashes;
      }
      _splitInteraction(interaction) {
          let splitStates = {};
          if (interaction) {
              let affectedStores = this._splitEventStore(interaction.affectedEvents, this._getKeysForEventDefs(interaction.affectedEvents));
              // can't rely on defKeys because event data is mutated
              let mutatedKeysByDefId = this._getKeysForEventDefs(interaction.mutatedEvents);
              let mutatedStores = this._splitEventStore(interaction.mutatedEvents, mutatedKeysByDefId);
              let populate = (key) => {
                  if (!splitStates[key]) {
                      splitStates[key] = {
                          affectedEvents: affectedStores[key] || EMPTY_EVENT_STORE,
                          mutatedEvents: mutatedStores[key] || EMPTY_EVENT_STORE,
                          isEvent: interaction.isEvent,
                      };
                  }
              };
              for (let key in affectedStores) {
                  populate(key);
              }
              for (let key in mutatedStores) {
                  populate(key);
              }
          }
          return splitStates;
      }
  }
  function buildEventUiForKey(allUi, eventUiForKey, individualUi) {
      let baseParts = [];
      if (allUi) {
          baseParts.push(allUi);
      }
      if (eventUiForKey) {
          baseParts.push(eventUiForKey);
      }
      let stuff = {
          '': combineEventUis(baseParts),
      };
      if (individualUi) {
          Object.assign(stuff, individualUi);
      }
      return stuff;
  }

  class AllDaySplitter extends Splitter {
      getKeyInfo() {
          return {
              allDay: {},
              timed: {},
          };
      }
      getKeysForDateSpan(dateSpan) {
          if (dateSpan.allDay) {
              return ['allDay'];
          }
          return ['timed'];
      }
      getKeysForEventDef(eventDef) {
          if (!eventDef.allDay) {
              return ['timed'];
          }
          if (hasBgRendering(eventDef)) {
              return ['timed', 'allDay'];
          }
          return ['allDay'];
      }
  }

  class DayTimeColsSlicer extends Slicer {
      sliceRange(range, dayRanges) {
          let segs = [];
          for (let col = 0; col < dayRanges.length; col += 1) {
              let segRange = intersectRanges(range, dayRanges[col]);
              if (segRange) {
                  segs.push({
                      startDate: segRange.start,
                      endDate: segRange.end,
                      isStart: segRange.start.valueOf() === range.start.valueOf(),
                      isEnd: segRange.end.valueOf() === range.end.valueOf(),
                      col,
                  });
              }
          }
          return segs;
      }
  }

  /*
  TODO: more DRY with daygrid?
  can be given null/undefined!
  */
  function organizeSegsByCol(segs, colCount) {
      let segsByCol = [];
      let i;
      for (i = 0; i < colCount; i += 1) {
          segsByCol.push([]);
      }
      if (segs) {
          for (i = 0; i < segs.length; i += 1) {
              segsByCol[segs[i].col].push(segs[i]);
          }
      }
      return segsByCol;
  }
  /*
  TODO: more DRY with daygrid?
  can be given null/undefined!
  */
  function splitInteractionByCol(ui, colCount) {
      let byRow = [];
      if (!ui) {
          for (let i = 0; i < colCount; i += 1) {
              byRow[i] = null;
          }
      }
      else {
          for (let i = 0; i < colCount; i += 1) {
              byRow[i] = {
                  affectedInstances: ui.affectedInstances,
                  isEvent: ui.isEvent,
                  segs: [],
              };
          }
          for (let seg of ui.segs) {
              byRow[seg.col].segs.push(seg);
          }
      }
      return byRow;
  }

  // potential nice values for the slot-duration and interval-duration
  // from largest to smallest
  const STOCK_SUB_DURATIONS = [
      { hours: 1 },
      { minutes: 30 },
      { minutes: 15 },
      { seconds: 30 },
      { seconds: 15 },
  ];
  function buildSlatMetas(slotMinTime, slotMaxTime, explicitLabelInterval, slotDuration, dateEnv) {
      let dayStart = new Date(0);
      let slatTime = slotMinTime;
      let slatIterator = createDuration(0);
      let labelInterval = explicitLabelInterval || computeLabelInterval(slotDuration);
      let metas = [];
      let i = 0;
      while (asRoughMs(slatTime) < asRoughMs(slotMaxTime)) {
          let date = dateEnv.add(dayStart, slatTime);
          let isLabeled = wholeDivideDurations(slatIterator, labelInterval) !== null;
          metas.push({
              date,
              time: slatTime,
              key: date.toISOString(), // we can't use the isoTimeStr for uniqueness when minTime/maxTime beyone 0h/24h
              isoTimeStr: formatIsoTimeString(date),
              isLabeled,
              isFirst: i === 0,
          });
          slatTime = addDurations(slatTime, slotDuration);
          slatIterator = addDurations(slatIterator, slotDuration);
          i += 1;
      }
      return metas;
  }
  // Computes an automatic value for slotHeaderInterval
  function computeLabelInterval(slotDuration) {
      let i;
      let labelInterval;
      let slotsPerLabel;
      // find the smallest stock label interval that results in more than one slots-per-label
      for (i = STOCK_SUB_DURATIONS.length - 1; i >= 0; i -= 1) {
          labelInterval = createDuration(STOCK_SUB_DURATIONS[i]);
          slotsPerLabel = wholeDivideDurations(labelInterval, slotDuration);
          if (slotsPerLabel !== null && slotsPerLabel > 1) {
              return labelInterval;
          }
      }
      return slotDuration; // fall back
  }

  class TimeGridAllDayHeader extends BaseComponent {
      constructor() {
          super(...arguments);
          // ref
          this.innerElRef = M$1();
      }
      render() {
          let { props } = this;
          let { options, viewApi } = this.context;
          let renderProps = {
              text: options.allDayText,
              view: viewApi,
              isNarrow: props.isNarrow,
          };
          return (u$1(ContentContainer, { tag: "div", attrs: {
                  role: 'rowheader',
              }, className: joinClassNames(classNames.flexRow, classNames.noMargin, classNames.noPadding, classNames.contentBox), style: {
                  width: props.width,
              }, renderProps: renderProps, generatorName: "allDayHeaderContent", customGenerator: options.allDayHeaderContent, defaultGenerator: renderAllDayInner, classNameGenerator: options.allDayHeaderClass, didMount: options.allDayHeaderDidMount, willUnmount: options.allDayHeaderWillUnmount, children: (InnerContent) => (u$1("div", { className: joinClassNames(classNames.flexRow, classNames.noShrink, classNames.whiteSpacePre), ref: this.innerElRef, children: u$1(InnerContent, { tag: 'div', className: generateClassName(options.allDayHeaderInnerClass, renderProps) }) })) }));
      }
      componentDidMount() {
          this._isUnmounting = false;
          const { props } = this;
          const innerEl = this.innerElRef.current; // TODO: make dynamic with useEffect
          // TODO: only attach this if refs props present
          this.disconnectInnerWidth = watchWidth(innerEl, (width) => {
              if (this._isUnmounting)
                  return;
              setRef(props.innerWidthRef, width);
          });
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.disconnectInnerWidth();
          setRef(this.props.innerWidthRef, null);
      }
  }
  function renderAllDayInner(renderProps) {
      return renderProps.text;
  }

  class TimeGridAllDayLane extends DateComponent {
      constructor() {
          super(...arguments);
          this.state = {};
          this.heightRef = M$1();
          this.handleMoreLinkEl = (el) => {
              this.disconnectMoreLinkHeight?.();
              this.disconnectMoreLinkHeight = undefined;
              if (el) {
                  this.disconnectMoreLinkHeight = watchHeight(el, (height) => {
                      if (this._isUnmounting)
                          return;
                      this.setState({ moreLinkHeight: height });
                  });
              }
          };
          this.handleRootEl = (rootEl) => {
              this.rootEl = rootEl;
              if (rootEl) {
                  this.context.registerInteractiveComponent(this, {
                      el: rootEl,
                  });
              }
              else {
                  this.context.unregisterInteractiveComponent(this);
              }
          };
      }
      render() {
          const { props, state } = this;
          const needsMoreLinkProbe = !props.forPrint && resolveDayGridPlacementMode(props.dayMaxEvents, props.dayMaxEventRows) === 'auto';
          return (u$1(S, { children: [u$1(DayGridRow, { ...props, moreLinkHeight: state.moreLinkHeight, 
                      /* BAD: these overwrite the props! caller might want to pass them */
                      rootElRef: this.handleRootEl, heightRef: this.heightRef }), needsMoreLinkProbe && (u$1(MoreLinkTrigger, { num: 1, display: 'row', isNarrow: props.cellIsNarrow, isMicro: props.cellIsMicro, elRef: this.handleMoreLinkEl, className: classNames.offscreen, attrs: {
                          'aria-hidden': true,
                          inert: '',
                      } }))] }));
      }
      componentDidMount() {
          this._isUnmounting = false;
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.disconnectMoreLinkHeight?.();
      }
      queryHit(isRtl, positionLeft, positionTop, elWidth) {
          const { props, heightRef } = this;
          const colCount = props.cells.length;
          const { col, left, right } = computeColFromPosition(positionLeft, elWidth, props.colWidth, colCount, isRtl);
          const cell = props.cells[col];
          const cellStartDate = cell.date;
          const cellEndDate = addDays(cellStartDate, 1);
          return {
              dateProfile: props.dateProfile,
              dateSpan: {
                  range: {
                      start: cellStartDate,
                      end: cellEndDate,
                  },
                  allDay: true,
                  ...cell.dateSpanProps,
              },
              getDayEl: () => getCellEl(this.rootEl, col),
              rect: {
                  left,
                  right,
                  top: 0,
                  bottom: heightRef.current,
              },
              layer: 0,
          };
      }
  }

  function computeSlatHeight(expandRows, slatCnt, explicitSlatMinHeight = 0, slatInnerHeight, // from the "inner" i think
  scrollerHeight) {
      if (!slatInnerHeight || !scrollerHeight) {
          return [undefined, false];
      }
      const slatMinHeight = Math.max(slatInnerHeight + 1, explicitSlatMinHeight);
      const slatLiquidHeight = scrollerHeight / slatCnt;
      let slatLiquid;
      let slatHeight;
      if (expandRows && slatLiquidHeight >= slatMinHeight) {
          slatLiquid = true;
          slatHeight = slatLiquidHeight;
      }
      else {
          slatLiquid = false;
          slatHeight = slatMinHeight;
      }
      return [slatHeight, slatLiquid];
  }
  /*
  A `startOfDayDate` must be given for avoiding ambiguity over how to treat midnight.
  */
  function computeDateTopFrac(date, dateProfile, startOfDayDate) {
      if (!startOfDayDate) {
          startOfDayDate = startOfDay(date);
      }
      return computeTimeTopFrac(createDuration(date.valueOf() - startOfDayDate.valueOf()), dateProfile);
  }
  function computeTimeTopFrac(time, dateProfile) {
      const startMs = asRoughMs(dateProfile.slotMinTime);
      const endMs = asRoughMs(dateProfile.slotMaxTime);
      let frac = (time.milliseconds - startMs) / (endMs - startMs);
      frac = Math.max(0, frac);
      frac = Math.min(1, frac);
      return frac;
  }

  /**
   * Projects production's date range onto the slat canvas.
   *
   * This is TimeGrid's production-specific coordinate conversion: it owns hidden
   * days, DST, and `eventMinHeight`. The shared engine consumes only the numbers
   * it produces.
   *
   * The canvas height may be assumed rather than measured — callers substitute
   * `ESTIMATED_SLAT_HEIGHT` so the first paint contains events — in which case
   * they also pass no `eventMinHeight`. A null height still yields no verticals,
   * but no production caller passes one.
   */
  function computeFgSegVerticals(segs, dateProfile, colDate, slatCnt, slatHeight, // in pixels
  eventMinHeight, // in pixels
  eventShortHeight) {
      const res = [];
      if (slatHeight != null) {
          const totalHeight = slatHeight * slatCnt;
          for (const seg of segs) {
              const startFrac = computeDateTopFrac(seg.startDate, dateProfile, colDate);
              const endFrac = computeDateTopFrac(seg.endDate, dateProfile, colDate);
              const startCoord = startFrac * totalHeight;
              let endCoord = endFrac * totalHeight;
              let height = endCoord - startCoord;
              if (eventMinHeight != null && height < eventMinHeight) {
                  height = eventMinHeight;
                  endCoord = startCoord + height;
              }
              res.push({
                  start: startCoord,
                  end: endCoord,
                  size: height,
                  isShort: height <= eventShortHeight,
              });
          }
      }
      return res;
  }
  /**
   * Adapts production TimeGrid segs to and from the shared placement engine.
   *
   * The caller owns vertical geometry: `segVerticals` already incorporates
   * clipping, and `eventMinHeight` too once the slat height is measured — the
   * caller withholds that floor while the height is only assumed. Any missing
   * entry is excluded. The engine owns only admission and normalized horizontal
   * placement. `slotEventOverlap` remains a final CSS concern, and mirrors
   * deliberately stay outside this normal-event admission path.
   */
  function buildTimeGridSegPlacements(segs, segVerticals, eventOrderStrict, eventMaxStack) {
      const sourceSegs = [];
      const segVerticalBySeg = new Map();
      for (let orderIndex = 0; orderIndex < segs.length; orderIndex += 1) {
          const seg = segs[orderIndex];
          const segVertical = segVerticals[orderIndex];
          if (segVertical) {
              const sourceSeg = {
                  ...seg,
                  key: seg.eventRange.instance.instanceId,
                  start: segVertical.start,
                  end: segVertical.end,
                  orderIndex,
              };
              sourceSegs.push(sourceSeg);
              segVerticalBySeg.set(sourceSeg, segVertical);
          }
      }
      const layout = layoutTimeGridColumnByMaxLevel(sourceSegs, eventMaxStack ?? Infinity, { orderStrict: eventOrderStrict ?? false });
      return {
          placements: layout.domOrderedPlacements.map((placement) => {
              const seg = placement.sourceSeg;
              return {
                  seg,
                  segVertical: segVerticalBySeg.get(seg),
                  levelCoord: placement.levelCoord,
                  thickness: placement.thickness,
                  stackDepth: placement.backwardDepth,
                  stackForward: placement.forwardDepth,
              };
          }),
          hiddenGroups: layout.moreLinkGroups.map((group) => {
              const groupSegs = group.hiddenSlices.map((slice) => slice.sourceSeg);
              return {
                  key: group.key,
                  start: group.start,
                  end: group.end,
                  segs: groupSegs,
              };
          }),
      };
  }
  /**
   * Builds, limits, and expands one TimeGrid day/resource column.
   *
   * TimeGrid rotates the visual meaning of the shared kernel's level structure.
   * A seg's lateral span runs down the time axis, while logical levels proceed
   * across the column. The retained levels become a normalized collision web:
   * connected components get equal base columns, and events widen through empty
   * deeper columns until their first collider.
   */
  function layoutTimeGridColumnByMaxLevel(eventOrderedSegs, maxLevels, options) {
      const { segLevels, excludedSegs } = buildSegLevels(eventOrderedSegs, options.orderStrict, maxLevels);
      const placements = positionTimeGridPlacements(segLevels);
      const moreLinkGroups = groupLaterallyIntersecting(convertSegsToWholeSlices(excludedSegs));
      return {
          domOrderedPlacements: sortByAxisOrder(placements),
          moreLinkGroups,
      };
  }
  /**
   * Turns retained dimensionless levels into normalized placement rectangles.
   *
   * Each connected collision component shares equal-width base columns. An
   * event then expands through consecutive deeper columns until the first one
   * containing a collider. A single intersection sweep supplies component
   * membership, expansion stops, and backward/forward longest-chain depths.
   */
  function positionTimeGridPlacements(levels) {
      const placementLevels = levels.map((level, levelIndex) => level.map((sourceSeg) => ({
          sourceSeg,
          start: sourceSeg.start,
          end: sourceSeg.end,
          isStart: sourceSeg.isStart,
          isEnd: sourceSeg.isEnd,
          levelIndex,
      })));
      // Level order matters below: every placement precedes its deeper colliders.
      const placements = flatArray(placementLevels);
      const collidersByKey = new Map();
      const parentByKey = new Map(placements.map((placement) => [
          placement.sourceSeg.key,
          placement.sourceSeg.key,
      ]));
      for (const placement of placements) {
          const colliders = [];
          for (let levelIndex = placement.levelIndex + 1; levelIndex < levels.length; levelIndex += 1) {
              colliders.push(...findIntersections(placementLevels[levelIndex], placement));
          }
          collidersByKey.set(placement.sourceSeg.key, colliders);
          for (const collider of colliders) {
              unionPlacementKeys(parentByKey, placement.sourceSeg.key, collider.sourceSeg.key);
          }
      }
      const maxLevelByRoot = new Map();
      for (const placement of placements) {
          const root = findPlacementRoot(parentByKey, placement.sourceSeg.key);
          maxLevelByRoot.set(root, Math.max(maxLevelByRoot.get(root) ?? 0, placement.levelIndex));
      }
      // Longest chains through the collision graph, as dynamic programming over
      // the adjacency. The passes run in opposite level orders so each dependency
      // is final before it contributes to the next placement.
      const backwardDepthByKey = new Map(placements.map((placement) => [
          placement.sourceSeg.key,
          0,
      ]));
      const forwardDepthByKey = new Map(placements.map((placement) => [
          placement.sourceSeg.key,
          0,
      ]));
      for (const placement of placements) {
          const depth = backwardDepthByKey.get(placement.sourceSeg.key) + 1;
          for (const collider of collidersByKey.get(placement.sourceSeg.key)) {
              backwardDepthByKey.set(collider.sourceSeg.key, Math.max(backwardDepthByKey.get(collider.sourceSeg.key), depth));
          }
      }
      for (let index = placements.length - 1; index >= 0; index -= 1) {
          const placement = placements[index];
          let depth = 0;
          for (const collider of collidersByKey.get(placement.sourceSeg.key)) {
              depth = Math.max(depth, forwardDepthByKey.get(collider.sourceSeg.key) + 1);
          }
          forwardDepthByKey.set(placement.sourceSeg.key, depth);
      }
      return placements.map((placement) => {
          const key = placement.sourceSeg.key;
          const levelCount = maxLevelByRoot.get(findPlacementRoot(parentByKey, key)) + 1;
          // Expand until the shallowest deeper collider. Colliders always share the
          // component, so their levels stay within its column count.
          let farLevel = levelCount;
          for (const collider of collidersByKey.get(key)) {
              farLevel = Math.min(farLevel, collider.levelIndex);
          }
          const levelCoord = placement.levelIndex / levelCount;
          const thickness = (farLevel - placement.levelIndex) / levelCount;
          return {
              ...placement,
              levelCoord,
              thickness,
              levelEndCoord: levelCoord + thickness,
              backwardDepth: backwardDepthByKey.get(key),
              forwardDepth: forwardDepthByKey.get(key),
          };
      });
  }
  function findPlacementRoot(parentByKey, key) {
      const parent = parentByKey.get(key);
      if (parent === key)
          return key;
      const root = findPlacementRoot(parentByKey, parent);
      parentByKey.set(key, root);
      return root;
  }
  function unionPlacementKeys(parentByKey, first, second) {
      const firstRoot = findPlacementRoot(parentByKey, first);
      const secondRoot = findPlacementRoot(parentByKey, second);
      if (firstRoot !== secondRoot)
          parentByKey.set(secondRoot, firstRoot);
  }

  /**
   * Slat height assumed on the first render, before the real one is measured.
   *
   * Without it, `computeFgSegVerticals` has no canvas to project onto and returns
   * nothing, so the view paints a frame containing no events at all and the
   * calendar looks empty until measurement lands. Projecting against an assumed
   * height instead means events are present in that very first paint.
   *
   * A flat constant is enough, and deliberately so. Placement compares segs
   * against each other and never against the axis length, so scaling every
   * coordinate by the same factor leaves collisions and level assignment
   * untouched. Guessing wrong rescales the raw geometry; it does not reorganize
   * it. That is why the caller withholds `eventMinHeight` while assuming — a
   * pixel floor applied at the wrong scale would stretch the wrong segs, and
   * stretching is what creates collisions.
   *
   * This is a claim about the raw coordinates only. The measured pass turns
   * `eventMinHeight` back on, and stretching a sub-minimum seg there can make it
   * collide with a neighbor it previously cleared, changing levels and
   * `eventMaxStack` admission. Expect the assumed pass to agree in the common
   * case; do not treat it as final.
   *
   * TimeGrid's caveat list stops there, unlike Timeline's: it places with unit
   * thickness and measures no event wrappers, so nothing about the rendered size
   * can feed back into placement. `isShort` also differs across passes, but that
   * is a styling decision rather than geometry.
   */
  const ESTIMATED_SLAT_HEIGHT = 50;

  // Firefox is terrible at rendering absolute elements that span across multiple print pages
  const isBrowserPrintQuirky = /* true || */ (typeof navigator !== 'undefined' &&
      navigator.userAgent.toLowerCase().includes('firefox'));
  function computeTimeGridPrintMode(forPrint, eventPrintLayout) {
      if (!forPrint) {
          return 'positioned';
      }
      return eventPrintLayout === 'stack' || (eventPrintLayout !== 'grid' && isBrowserPrintQuirky)
          ? 'stack'
          : 'positioned';
  }

  const DEFAULT_TIME_FORMAT$1 = createFormatter({
      hour: 'numeric',
      minute: '2-digit',
      meridiem: false,
  });
  class TimeGridEvent extends BaseComponent {
      render() {
          const { props } = this;
          return (u$1(StandardEvent, { ...props, display: 'column', level: props.level, isNarrow: props.isNarrow, isShort: props.isShort, className: 
              // see note in TimeGridCol on why we use flexbox
              props.isLiquid ? classNames.liquid : '', disableLiquid: !props.isLiquid, defaultTimeFormat: DEFAULT_TIME_FORMAT$1 }));
      }
  }

  class TimeGridMoreLink extends BaseComponent {
      render() {
          let { props } = this;
          return (u$1("div", { className: joinClassNames(classNames.abs, classNames.flexCol, classNames.end0, classNames.z9999), style: {
                  top: props.top,
                  height: props.height,
              }, children: u$1(MoreLinkContainer, { className: classNames.liquid, display: 'column', allDayDate: null, segs: props.hiddenSegs, hiddenSegs: props.hiddenSegs, dateSpanProps: props.dateSpanProps, dateProfile: props.dateProfile, todayRange: props.todayRange, popoverContent: () => renderPlainFgSegs(props.hiddenSegs, props, /* isMirror = */ false), forceTimed: true, isNarrow: props.isNarrow, isMicro: props.isMicro }) }));
      }
  }

  const NowIndicatorDot = (props) => (u$1(ViewContextType.Consumer, { children: (context) => {
          let { options } = context;
          return (u$1("div", { className: joinClassNames(props.className, options.nowIndicatorDotClass), style: props.style }));
      } }));

  const NowIndicatorLineContainer = (props) => (u$1(ViewContextType.Consumer, { children: (context) => {
          let { options } = context;
          let renderProps = {
              date: context.dateEnv.toDate(props.date),
              view: context.viewApi,
          };
          return (u$1(ContentContainer, { elRef: props.elRef, tag: props.tag || 'div', attrs: props.attrs, className: props.className, style: props.style, renderProps: renderProps, generatorName: "nowIndicatorLineContent", customGenerator: options.nowIndicatorLineContent, classNameGenerator: options.nowIndicatorLineClass, didMount: options.nowIndicatorLineDidMount, willUnmount: options.nowIndicatorLineWillUnmount, children: props.children }));
      } }));

  /*
  Renders both the line AND the dot
  TODO: DRY with other NowIndicator components
  */
  function TimeGridNowIndicatorLine(props) {
      const top = props.totalHeight != null
          ? props.totalHeight * computeDateTopFrac(props.nowDate, props.dateProfile, props.dayDate)
          : undefined;
      return (u$1("div", { className: joinClassNames(classNames.fill, classNames.pointerEventsNone, classNames.z2), children: [u$1(NowIndicatorLineContainer, { className: joinClassNames(classNames.fillX, classNames.noMarginX, classNames.borderlessX), style: { top }, date: props.nowDate }), (props.showDot ?? true) && (u$1(NowIndicatorDot, { className: joinClassNames(classNames.abs, classNames.start0), style: { top } }))] }));
  }

  class TimeGridCol extends BaseComponent {
      constructor() {
          super(...arguments);
          this.sortEventSegs = memoize(sortEventSegs);
          this.getDateMeta = memoize(getDateMeta);
      }
      render() {
          let { props, context } = this;
          let { options, dateEnv } = context;
          let isSelectMirror = options.selectMirror;
          let mirrorSegs = // yuck
           (props.eventDrag && props.eventDrag.segs) ||
              (props.eventResize && props.eventResize.segs) ||
              (isSelectMirror && props.dateSelectionSegs) ||
              [];
          let dateMeta = this.getDateMeta(props.date, dateEnv, props.dateProfile, props.todayRange);
          const baseClassName = joinClassNames(classNames.borderlessY, classNames.borderlessEnd, !props.borderStart && classNames.borderlessStart, props.width == null && classNames.liquid, classNames.rel, // origin for abs-positioned children within
          classNames.z1);
          const baseStyle = {
              width: props.width,
          };
          const isStack = this.getIsStack();
          const renderProps = {
              ...dateMeta,
              ...props.renderProps,
              isStack,
              isNarrow: props.isNarrow,
              isMajor: props.isMajor,
              view: context.viewApi,
          };
          if (dateMeta.isDisabled) {
              return (u$1("div", { role: 'gridcell', "aria-disabled": true, className: joinClassNames(generateClassName(options.dayLaneClass, renderProps), baseClassName), style: baseStyle }));
          }
          const innerClassName = joinClassNames(generateClassName(options.dayLaneInnerClass, renderProps), !isStack && classNames.fill, classNames.z1);
          const sortedFgSegs = this.sortEventSegs(props.fgEventSegs, options.eventOrder);
          return (u$1(ContentContainer, { tag: "div", attrs: {
                  ...props.attrs,
                  role: 'gridcell',
                  ...(dateMeta.isToday ? { 'aria-current': 'date' } : {}),
                  'data-date': formatDayString(props.date),
              }, className: baseClassName, style: baseStyle, renderProps: renderProps, generatorName: undefined, classNameGenerator: options.dayLaneClass, didMount: options.dayLaneDidMount, willUnmount: options.dayLaneWillUnmount, children: () => (u$1(S, { children: [this.renderFillSegs(props.businessHourSegs, 'non-business'), this.renderFillSegs(props.bgEventSegs, 'bg-event'), this.renderFillSegs(props.dateSelectionSegs, 'highlight'), u$1("div", { className: innerClassName, children: this.renderFgSegs(sortedFgSegs, 
                          /* isMirror = */ false) }), Boolean(mirrorSegs.length) && (
                      // but only show it when there are actual mirror events, to avoid blocking clicks
                      u$1("div", { className: innerClassName, children: this.renderFgSegs(mirrorSegs, 
                          /* isMirror = */ true) })), this.renderNowIndicator(props.nowIndicatorSegs)] })) }));
      }
      renderFgSegs(sortedFgSegs, isMirror) {
          const { props } = this;
          if (this.getIsStack()) {
              return renderPlainFgSegs(sortedFgSegs, props, isMirror);
          }
          if (isMirror) {
              return this.renderPositionedMirrorSegs(sortedFgSegs);
          }
          return this.renderPositionedFgSegs(sortedFgSegs);
      }
      renderPositionedFgSegs(segs) {
          let { eventMaxStack, eventOrderStrict } = this.context.options;
          let segVerticals = this.computeSegVerticals(segs);
          let { placements, hiddenGroups } = buildTimeGridSegPlacements(segs, segVerticals, eventOrderStrict, eventMaxStack);
          return (u$1(S, { children: [placements.map((placement) => this.renderPositionedSeg(placement.seg, placement.segVertical, this.computeSegHStyle(placement), placement.stackDepth, 
                  /* isMirror = */ false)), this.renderHiddenGroups(hiddenGroups)] }));
      }
      // Mirrors bypass normal-event admission so limits cannot hide them or create more links.
      renderPositionedMirrorSegs(segs) {
          let segVerticals = this.computeSegVerticals(segs);
          return segs.map((seg, index) => this.renderPositionedSeg(seg, segVerticals[index] || {}, { left: 0, right: 0, zIndex: 0 }, // full column width
          /* level = */ 0, 
          /* isMirror = */ true));
      }
      renderPositionedSeg(seg, segVertical, hStyle, level, isMirror) {
          let { props } = this;
          let { eventRange } = seg;
          let { instanceId } = eventRange.instance; // guaranteed because it's an fg event
          let isSelected = instanceId === props.eventSelection;
          if (isSelected) {
              hStyle.zIndex += 1000; // HACK: relies on hardcoded z-index offset; fragile if stacking context changes
          }
          let isDragging = Boolean(props.eventDrag && props.eventDrag.affectedInstances[instanceId]);
          let isResizing = Boolean(props.eventResize && props.eventResize.affectedInstances[instanceId]);
          let isInvisible = !isMirror && (isDragging || isResizing);
          return (u$1("div", { 
              // we would have used classNames.fill, but multi-page spanning breaks in Firefox
              // we would have used height:100%, but multi-page spanning breaks in Safari
              className: joinClassNames(classNames.abs, classNames.flexCol), style: {
                  visibility: isInvisible ? 'hidden' : undefined,
                  top: segVertical.start,
                  height: segVertical.size,
                  ...hStyle,
              }, children: u$1(TimeGridEvent, { eventRange: eventRange, slicedStart: seg.startDate, slicedEnd: seg.endDate, isStart: seg.isStart, isEnd: seg.isEnd, isDragging: isDragging, isResizing: isResizing, isMirror: isMirror, isSelected: isSelected, level: level, isNarrow: props.isNarrow, isShort: segVertical.isShort || false, isLiquid: true, ...getEventRangeMeta(eventRange, props.todayRange, props.nowDate, props.nowMs) }) }, instanceId));
      }
      /*
      A pixel floor is only meaningful against a real slat height, so it stays off
      while the height is assumed. See ESTIMATED_SLAT_HEIGHT for why, and for what
      the assumed pass does and does not guarantee.
      */
      // TODO: memoize this?
      computeSegVerticals(segs) {
          let { props, context } = this;
          let isMeasured = props.slatHeight != null;
          return computeFgSegVerticals(segs, props.dateProfile, props.date, props.slatCnt, props.slatHeight ?? ESTIMATED_SLAT_HEIGHT, isMeasured ? context.options.eventMinHeight : undefined, context.options.eventShortHeight);
      }
      /*
      NOTE: a group's coordinates come from computeFgSegVerticals, so eventMinHeight
      has already been applied to the segs it was formed from
      */
      renderHiddenGroups(hiddenGroups) {
          let { dateSpanProps, dateProfile, todayRange, nowDate, nowMs, eventSelection, eventDrag, eventResize, isNarrow, isMicro } = this.props;
          return (u$1(S, { children: hiddenGroups.map((hiddenGroup) => {
                  return (u$1(TimeGridMoreLink, { hiddenSegs: hiddenGroup.segs, top: hiddenGroup.start, height: hiddenGroup.end - hiddenGroup.start, isNarrow: isNarrow, isMicro: isMicro, dateSpanProps: dateSpanProps, dateProfile: dateProfile, todayRange: todayRange, nowDate: nowDate, nowMs: nowMs, eventSelection: eventSelection, eventDrag: eventDrag, eventResize: eventResize }, hiddenGroup.key));
              }) }));
      }
      renderFillSegs(segs, fillType) {
          let { props, context } = this;
          let segVerticals = this.computeSegVerticals(segs);
          return (u$1(S, { children: segs.map((seg, index) => {
                  const { eventRange } = seg;
                  const segVertical = segVerticals[index] || {};
                  return (u$1("div", { className: classNames.fillX, style: {
                          top: segVertical.start,
                          height: segVertical.size,
                          // HACK to get bg fills to overlap cell-start border
                          // which matches how dayGrid looks,
                          // which is important because all-day background events, in TimeGrid,
                          // will render on both at the same time
                          marginInlineStart: -1,
                      }, children: fillType === 'bg-event' ?
                          u$1(BgEvent, { eventRange: eventRange, isStart: seg.isStart, isEnd: seg.isEnd, isNarrow: props.isNarrow, isShort: segVertical.isShort || false, isVertical: true, ...getEventRangeMeta(eventRange, props.todayRange, props.nowDate, props.nowMs) }) :
                          renderFill(fillType, context.options) }, buildEventRangeKey(eventRange)));
              }) }));
      }
      renderNowIndicator(segs) {
          let { props } = this;
          if (props.forPrint || this.getIsStack()) {
              return;
          }
          return segs.map((seg, i) => (u$1(TimeGridNowIndicatorLine, { nowDate: seg.startDate, dayDate: props.date, dateProfile: props.dateProfile, totalHeight: props.slatHeight != null ? props.slatHeight * props.slatCnt : undefined, showDot: seg.showDot ?? true }, i)));
      }
      /*
      TODO: eventually move to width, not left+right
      */
      computeSegHStyle(segRect) {
          let { options } = this.context;
          let shouldOverlap = options.slotEventOverlap;
          let nearCoord = segRect.levelCoord; // the left side if LTR. the right side if RTL. floating-point
          let farCoord = segRect.levelCoord + segRect.thickness; // the right side if LTR. the left side if RTL. floating-point
          if (shouldOverlap) {
              // double the width, but don't go beyond the maximum forward coordinate (1.0)
              farCoord = Math.min(1, nearCoord + (farCoord - nearCoord) * 2);
          }
          let props = {
              zIndex: segRect.stackDepth + 1, // convert from 0-base to 1-based
              insetInlineStart: fracToCssDim(nearCoord),
              insetInlineEnd: fracToCssDim(1 - farCoord),
              marginInlineEnd: undefined,
          };
          if (shouldOverlap && segRect.stackForward) {
              // add padding to the edge so that forward stacked events don't cover the resizer's icon
              props.marginInlineEnd = 10 * 2; // 10 is a guesstimate of the icon's width
          }
          return props;
      }
      getIsStack() {
          const { eventPrintLayout } = this.context.options;
          return computeTimeGridPrintMode(this.props.forPrint, eventPrintLayout) === 'stack';
      }
  }
  function renderPlainFgSegs(sortedFgSegs, { todayRange, nowDate, nowMs, eventSelection, eventDrag, eventResize }, isMirror) {
      return (u$1(S, { children: sortedFgSegs.map((seg) => {
              let { eventRange } = seg;
              let { instanceId } = eventRange.instance;
              let isDragging = Boolean(eventDrag && eventDrag.affectedInstances[instanceId]);
              let isResizing = Boolean(eventResize && eventResize.affectedInstances[instanceId]);
              let isInvisible = isDragging || isResizing;
              return (u$1("div", { className: classNames.breakInsideAvoid, style: { visibility: isInvisible ? 'hidden' : undefined }, children: u$1(TimeGridEvent, { eventRange: eventRange, slicedStart: seg.startDate, slicedEnd: seg.endDate, isStart: seg.isStart, isEnd: seg.isEnd, isDragging: isDragging, isResizing: isResizing, isMirror: isMirror, isSelected: instanceId === eventSelection, level: 0, isShort: false, isNarrow: false, disableResizing: true, ...getEventRangeMeta(eventRange, todayRange, nowDate, nowMs) }) }, instanceId));
          }) }));
  }

  class TimeGridCols extends DateComponent {
      constructor() {
          super(...arguments);
          // memo
          this.processSlotOptions = memoize(processSlotOptions);
          this.handleRootEl = (el) => {
              this.rootEl = el;
              if (el) {
                  this.context.registerInteractiveComponent(this, {
                      el,
                      isHitComboAllowed: this.props.isHitComboAllowed,
                  });
              }
              else {
                  this.context.unregisterInteractiveComponent(this);
              }
          };
      }
      render() {
          const { props } = this;
          return (u$1("div", { role: props.role /* !!! */, className: joinClassNames(props.className, classNames.flexRow), ref: this.handleRootEl, children: props.cells.map((cell, col) => (u$1(TimeGridCol, { dateProfile: props.dateProfile, nowDate: props.nowDate, nowMs: props.nowMs, todayRange: props.todayRange, date: cell.date, isMajor: cell.isMajor, slatCnt: props.slatCnt, renderProps: cell.renderProps, attrs: cell.attrs, dateSpanProps: cell.dateSpanProps, forPrint: props.forPrint, borderStart: Boolean(col), isNarrow: props.cellIsNarrow, isMicro: props.cellIsMicro, 
                  // content
                  fgEventSegs: props.fgEventSegsByCol[col], bgEventSegs: props.bgEventSegsByCol[col], businessHourSegs: props.businessHourSegsByCol[col], nowIndicatorSegs: props.nowIndicatorSegsByCol[col], dateSelectionSegs: props.dateSelectionSegsByCol[col], eventDrag: props.eventDragByCol[col], eventResize: props.eventResizeByCol[col], eventSelection: props.eventSelection, 
                  // dimensions
                  width: props.colWidth, slatHeight: props.slatHeight }, cell.key))) }));
      }
      queryHit(isRtl, positionLeft, positionTop, elWidth) {
          const { dateProfile, cells, colWidth, slatHeight } = this.props;
          const { dateEnv, options } = this.context;
          const { snapDuration, snapsPerSlot } = this.processSlotOptions(options.slotDuration, options.snapDuration);
          const colCount = cells.length;
          const { col, left, right } = computeColFromPosition(positionLeft, elWidth, colWidth, colCount, isRtl);
          const cell = cells[col];
          const slatIndex = Math.floor(positionTop / slatHeight);
          const slatTop = slatIndex * slatHeight;
          const partial = (positionTop - slatTop) / slatHeight; // floating point number between 0 and 1
          const localSnapIndex = Math.floor(partial * snapsPerSlot); // the snap # relative to start of slat
          const snapIndex = slatIndex * snapsPerSlot + localSnapIndex;
          const time = addDurations(dateProfile.slotMinTime, multiplyDuration(snapDuration, snapIndex));
          const start = dateEnv.add(cell.date, time);
          const end = dateEnv.add(start, snapDuration);
          return {
              dateProfile,
              dateSpan: {
                  range: { start, end },
                  allDay: false,
                  ...cell.dateSpanProps,
              },
              getDayEl: () => getCellEl(this.rootEl, col),
              rect: {
                  left,
                  right,
                  top: slatTop,
                  bottom: slatTop + slatHeight,
              },
              layer: 0,
          };
      }
  }
  TimeGridCols.addPropsEquality({
      style: isPropsEqualShallow,
  });
  // Utils
  // -------------------------------------------------------------------------------------------------
  function processSlotOptions(slotDuration, snapDurationOverride) {
      let snapDuration = snapDurationOverride || slotDuration;
      let snapsPerSlot = wholeDivideDurations(slotDuration, snapDuration);
      if (snapsPerSlot === null) {
          snapDuration = slotDuration;
          snapsPerSlot = 1;
          // TODO: say warning?
      }
      return { snapDuration, snapsPerSlot };
  }

  const NowIndicatorHeaderContainer = (props) => (u$1(ViewContextType.Consumer, { children: (context) => {
          let { options } = context;
          let renderProps = {
              date: context.dateEnv.toDate(props.date),
              view: context.viewApi,
          };
          return (u$1(ContentContainer, { elRef: props.elRef, tag: props.tag || 'div', attrs: props.attrs, className: props.className, style: props.style, renderProps: renderProps, generatorName: "nowIndicatorHeaderContent", customGenerator: options.nowIndicatorHeaderContent, classNameGenerator: options.nowIndicatorHeaderClass, didMount: options.nowIndicatorHeaderDidMount, willUnmount: options.nowIndicatorHeaderWillUnmount, children: props.children }));
      } }));

  /*
  TODO: DRY with other NowIndicator components
  */
  function TimeGridNowIndicatorArrow(props) {
      return (u$1("div", { 
          // crop any overflow that the arrow/line might cause
          // TODO: just do this on the entire canvas within the scroller
          className: joinClassNames(classNames.fill, classNames.crop, classNames.pointerEventsNone, classNames.z2), children: u$1(NowIndicatorHeaderContainer, { className: classNames.abs, style: {
                  top: props.totalHeight != null
                      ? props.totalHeight * computeDateTopFrac(props.nowDate, props.dateProfile)
                      : undefined
              }, date: props.nowDate }) }));
  }

  const DEFAULT_SLAT_LABEL_FORMAT = createFormatter({
      hour: 'numeric',
      minute: '2-digit',
      omitZeroMinute: true,
      meridiem: 'short',
  });
  /*
  Always oriented in a column
  */
  class TimeGridSlatHeader extends BaseComponent {
      constructor() {
          super(...arguments);
          // memo
          this.createRenderProps = memoize(createRenderProps);
          // ref
          this.innerElRef = M$1();
      }
      render() {
          let { props, context } = this;
          let { options } = context;
          let headerFormat = // TODO: fully pre-parse
           options.slotHeaderFormat == null ? DEFAULT_SLAT_LABEL_FORMAT :
              Array.isArray(options.slotHeaderFormat) ? createFormatter(options.slotHeaderFormat[0]) :
                  createFormatter(options.slotHeaderFormat);
          let renderProps = this.createRenderProps(props.date, props.time, !props.isLabeled, props.isNarrow, props.isFirst, headerFormat, context);
          let className = joinClassNames(props.liquidHeight && classNames.liquid, classNames.flexRow, classNames.alignStart, classNames.noMargin, classNames.noPadding, classNames.borderlessX, classNames.borderlessBottom, !props.borderTop && classNames.borderlessTop);
          if (!props.isLabeled) {
              return (u$1("div", { className: joinClassNames(generateClassName(options.slotHeaderClass, renderProps), className), style: {
                      height: props.height,
                  } }));
          }
          return (u$1(ContentContainer, { tag: "div", attrs: {
                  'data-time': props.isoTimeStr,
              }, style: {
                  height: props.height,
              }, className: className, renderProps: renderProps, generatorName: "slotHeaderContent", customGenerator: options.slotHeaderContent, defaultGenerator: renderInnerContent, classNameGenerator: options.slotHeaderClass, didMount: options.slotHeaderDidMount, willUnmount: options.slotHeaderWillUnmount, children: (InnerContent) => (u$1("div", { ref: this.innerElRef, className: joinClassNames(classNames.noShrink, classNames.whiteSpaceNoWrap, classNames.flexRow), children: u$1(InnerContent, { tag: "div", className: generateClassName(options.slotHeaderInnerClass, renderProps) }) })) }));
      }
      componentDidMount() {
          this._isUnmounting = false;
          const { props } = this;
          const innerEl = this.innerElRef.current; // TODO: make dynamic with useEffect
          if (innerEl) { // could be null if !isLabeled
              // TODO: only attach this if refs props present
              // TODO: fire width/height independently?
              this.disconnectInnerSize = watchSize(innerEl, (width, height) => {
                  if (this._isUnmounting)
                      return;
                  setRef(props.innerWidthRef, width);
                  setRef(props.innerHeightRef, height);
              });
          }
      }
      componentWillUnmount() {
          const { props } = this;
          this._isUnmounting = true;
          if (this.disconnectInnerSize) {
              this.disconnectInnerSize();
              setRef(props.innerWidthRef, null);
              setRef(props.innerHeightRef, null);
          }
      }
  }
  function createRenderProps(date, time, isMinor, isNarrow, isFirst, headerFormat, context) {
      return {
          // this is a time-specific slot. not day-specific, so don't do today/nowRange
          ...getDateMeta(date, context.dateEnv),
          level: 0, // axis level (for when multiple axes)
          text: joinDateTimeFormatParts(context.dateEnv.formatToParts(date, headerFormat)),
          time: time,
          isMajor: false,
          isMinor,
          isTime: true,
          isNarrow,
          hasNavLink: false,
          isFirst,
          view: context.viewApi,
      };
  }
  function renderInnerContent(props) {
      return props.text;
  }

  class TimeGridSlatLane extends BaseComponent {
      constructor() {
          super(...arguments);
          // memo
          this.getDateMeta = memoize(getDateMeta);
      }
      render() {
          let { props, context } = this;
          let { options } = context;
          let renderProps = {
              // this is a time-specific slot. not day-specific, so don't do today/nowRange
              ...this.getDateMeta(props.date, context.dateEnv),
              time: props.time,
              isMajor: false,
              isMinor: !props.isLabeled,
              view: context.viewApi,
          };
          return (u$1(ContentContainer, { tag: "div", attrs: {
                  'data-time': props.isoTimeStr,
              }, className: joinClassNames(classNames.noMargin, classNames.noPadding, classNames.liquid, classNames.borderlessX, classNames.borderlessBottom, !props.borderTop && classNames.borderlessTop), renderProps: renderProps, generatorName: undefined, classNameGenerator: options.slotLaneClass, didMount: options.slotLaneDidMount, willUnmount: options.slotLaneWillUnmount }));
      }
  }

  const DEFAULT_WEEK_NUM_FORMAT = createFormatter({ week: 'short' });
  class TimeGridWeekNumber extends BaseComponent {
      constructor() {
          super(...arguments);
          // ref
          this.innerElRef = M$1();
      }
      render() {
          let { props, context } = this;
          let { options, dateEnv } = context;
          let range = props.dateProfile.renderRange;
          let dayCnt = diffDays(range.start, range.end);
          // HACK: only make week-number a nav-link when NOT in week-view
          let hasNavLink = dayCnt === 1 && options.navLinks;
          let weekDateMarker = range.start;
          let fullDateStr = buildDateStr(context, weekDateMarker, 'week');
          let weekNum = dateEnv.computeWeekNumber(weekDateMarker);
          let weekTextParts = dateEnv.formatToParts(weekDateMarker, options.weekNumberFormat || DEFAULT_WEEK_NUM_FORMAT);
          let weekText = joinDateTimeFormatParts(weekTextParts);
          let weekDateZoned = dateEnv.toDate(weekDateMarker);
          const weekNumberRenderProps = {
              num: weekNum,
              text: weekText,
              textParts: weekTextParts,
              date: weekDateZoned,
              isNarrow: props.isNarrow,
              hasNavLink,
              options: { dayMinWidth: options.dayMinWidth },
          };
          return (u$1(ContentContainer, { tag: 'div', attrs: {
                  role: 'gridcell', // doesn't always describe other cells in row, so make generic
                  'aria-label': fullDateStr,
              }, className: joinClassNames(classNames.flexRow, classNames.noMargin, classNames.noPadding, props.isLiquid ? classNames.liquid : classNames.contentBox), style: {
                  width: props.width,
              }, renderProps: weekNumberRenderProps, generatorName: "weekNumberHeaderContent", customGenerator: options.weekNumberHeaderContent, defaultGenerator: renderText$1, classNameGenerator: options.weekNumberHeaderClass, didMount: options.weekNumberHeaderDidMount, willUnmount: options.weekNumberHeaderWillUnmount, children: (InnerContent) => (u$1("div", { ref: this.innerElRef, className: joinClassNames(classNames.flexRow, classNames.noShrink, classNames.whiteSpaceNoWrap), children: u$1(InnerContent, { tag: 'div', attrs: hasNavLink
                          ? buildNavLinkAttrs(context, range.start, 'week', fullDateStr)
                          : { 'aria-label': fullDateStr }, className: generateClassName(options.weekNumberHeaderInnerClass, weekNumberRenderProps) }) })) }));
      }
      componentDidMount() {
          this._isUnmounting = false;
          const { props } = this;
          const innerEl = this.innerElRef.current; // TODO: make dynamic with useEffect
          // TODO: only attach this if refs props present
          // TODO: handle width/height independently?
          this.disconnectInnerSize = watchSize(innerEl, (width, height) => {
              if (this._isUnmounting)
                  return;
              setRef(props.innerWidthRef, width);
              setRef(props.innerHeightRef, height);
          });
      }
      componentWillUnmount() {
          const { props } = this;
          this._isUnmounting = true;
          this.disconnectInnerSize();
          setRef(props.innerWidthRef, null);
          setRef(props.innerHeightRef, null);
      }
  }

  function TimeGridAxisEmpty(props) {
      return (u$1("div", { role: 'gridcell' // is empty so can't be rowheader/columnheader
          , className: props.isLiquid ? classNames.liquid : classNames.contentBox, style: { width: props.width } }));
  }

  class TimeGridLayoutPannable extends BaseComponent {
      constructor() {
          super(...arguments);
          this.state = {
              headerTierHeights: [],
          };
          // refs
          this.headerLabelInnerWidthRefMap = new RefMap(() => {
              afterSize(this.handleAxisWidths);
          });
          this.headerLabelInnerHeightRefMap = new RefMap(() => {
              afterSize(this.handleHeaderHeights);
          });
          this.headerMainInnerHeightRefMap = new RefMap(() => {
              afterSize(this.handleHeaderHeights);
          });
          this.handleAllDayLabelInnerWidth = (width) => {
              this.allDayLabelInnerWidth = width;
              afterSize(this.handleAxisWidths);
          };
          this.slatLabelInnerWidthRefMap = new RefMap(() => {
              afterSize(this.handleAxisWidths);
          });
          this.slatLabelInnerHeightRefMap = new RefMap(() => {
              afterSize(this.handleSlatInnerHeights);
          });
          this.headerScrollerRef = M$1();
          this.allDayScrollerRef = M$1();
          this.mainScrollerRef = M$1();
          this.footScrollerRef = M$1();
          this.axisScrollerRef = M$1();
          // Sizing
          // -----------------------------------------------------------------------------------------------
          this.handleTotalWidth = (totalWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ totalWidth });
          };
          this.handleBodyHeight = (bodyHeight) => {
              if (this._isUnmounting)
                  return;
              this.setState({ bodyHeight });
          };
          this.handleClientWidth = (clientWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ clientWidth });
          };
          this.handleClientHeight = (clientHeight) => {
              if (this._isUnmounting)
                  return;
              this.setState({ clientHeight });
          };
          this.handleStickyBottomScrollbarWidth = (sticykBottomScrollbarWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ sticykBottomScrollbarWidth });
          };
          this.handleHeaderHeights = () => {
              if (this._isUnmounting)
                  return;
              const headerLabelInnerHeightMap = this.headerLabelInnerHeightRefMap.current;
              const headerMainInnerHeightMap = this.headerMainInnerHeightRefMap.current;
              const heights = [];
              // important to loop using 'main' because 'label' might not be tracking height if empty
              for (const [tierNum, mainHeight] of headerMainInnerHeightMap.entries()) {
                  heights[tierNum] = Math.max(headerLabelInnerHeightMap.get(tierNum) || 0, mainHeight);
              }
              this.setState({ headerTierHeights: heights });
          };
          this.handleSlatInnerHeights = () => {
              if (this._isUnmounting)
                  return;
              const slatLabelInnerHeightMap = this.slatLabelInnerHeightRefMap.current;
              let max = 0;
              for (const slatLabelInnerHeight of slatLabelInnerHeightMap.values()) {
                  max = Math.max(max, slatLabelInnerHeight);
              }
              if (this.state.slatInnerHeight !== max) {
                  this.setState({ slatInnerHeight: max });
              }
          };
          this.handleAxisWidths = () => {
              if (this._isUnmounting)
                  return;
              const headerLabelInnerWidthMap = this.headerLabelInnerWidthRefMap.current;
              const slatLabelInnerWidthMap = this.slatLabelInnerWidthRefMap.current;
              let max = this.allDayLabelInnerWidth || 0; // guard against all-day slot hidden
              for (const headerLabelInnerWidth of headerLabelInnerWidthMap.values()) {
                  max = Math.max(max, headerLabelInnerWidth);
              }
              for (const slatLableInnerWidth of slatLabelInnerWidthMap.values()) {
                  max = Math.max(max, slatLableInnerWidth);
              }
              if (this.state.axisWidth !== max) {
                  this.setState({ axisWidth: max });
              }
          };
      }
      render() {
          const { props, state, context, headerLabelInnerWidthRefMap, headerLabelInnerHeightRefMap, headerMainInnerHeightRefMap, slatLabelInnerWidthRefMap, slatLabelInnerHeightRefMap, } = this;
          const { nowDate, headerTiers, forPrint } = props;
          const nowTimeMs = nowDate.valueOf() - startOfDay(nowDate).valueOf();
          const { axisWidth, totalWidth, clientWidth, clientHeight, bodyHeight, sticykBottomScrollbarWidth } = state;
          const { options } = context;
          const { borderlessX, borderlessTop, borderlessBottom } = computeViewBorderless(options);
          const endScrollbarWidth = (totalWidth != null && clientWidth != null && axisWidth != null)
              ? totalWidth - clientWidth - (axisWidth + 1) // +1 for hardcoded divider!
              : undefined;
          const verticalScrolling = !forPrint && !getIsHeightAuto(options);
          const tableHeaderSticky = !forPrint && getTableHeaderSticky(options);
          const footerScrollbarSticky = !forPrint && getFooterScrollbarSticky(options);
          const printStackEnabled = computeTimeGridPrintMode(forPrint, options.eventPrintLayout) === 'stack';
          const absPrint = forPrint && !printStackEnabled;
          const simplePrint = forPrint && printStackEnabled;
          const colCount = props.cells.length;
          const [canvasWidth, appliedColWidth] = computeColWidth(colCount, props.dayMinWidth, clientWidth);
          const measuredColWidth = appliedColWidth ?? (clientWidth != null ? clientWidth / colCount : undefined);
          const cellIsMicro = measuredColWidth != null && measuredColWidth <= dayMicroWidth;
          const cellIsNarrow = cellIsMicro || (measuredColWidth != null && measuredColWidth <= options.dayNarrowWidth);
          const slatCnt = props.slatMetas.length;
          const [slatHeight, slatLiquidHeight] = computeSlatHeight(// TODO: memo?
          verticalScrolling && options.expandRows, slatCnt, options.slotMinHeight, state.slatInnerHeight, clientHeight);
          this.slatHeight = slatHeight;
          // TODO: have computeSlatHeight return?
          const totalSlatHeight = (slatHeight || 0) * slatCnt;
          const forcedBodyHeight = absPrint ? totalSlatHeight : undefined;
          const rowsNotExpanding = verticalScrolling && !options.expandRows &&
              clientHeight != null && clientHeight > totalSlatHeight;
          const firstBodyRowIndex = options.dayHeaders ? headerTiers.length + 1 : 1;
          const bottomScrollbarWidth = footerScrollbarSticky
              ? sticykBottomScrollbarWidth
              : (bodyHeight != null && clientHeight != null)
                  ? (bodyHeight - clientHeight)
                  : undefined;
          return (u$1(S, { children: [options.dayHeaders && (u$1("div", { className: joinClassNames(generateClassName(options.tableHeaderClass, {
                          isSticky: tableHeaderSticky,
                          borderlessX,
                          borderlessTop,
                          borderlessBottom,
                          multiMonthColumns: 0,
                      }), 
                      // See the note in TimeGridLayout about why print doesn't use repeating headers.
                      classNames.flexCol, tableHeaderSticky && classNames.tableHeaderSticky, classNames.z1), children: [u$1("div", { className: classNames.flexRow, children: [u$1("div", { role: 'rowgroup', className: classNames.contentBox, style: { width: axisWidth }, children: headerTiers.map((rowConfig, tierNum) => (u$1("div", { role: 'row', "aria-rowindex": tierNum + 1, className: joinClassNames(options.dayHeaderRowClass, classNames.flexRow, classNames.contentBox, classNames.borderlessX, classNames.borderlessTop, tierNum === props.headerTiers.length - 1 && classNames.borderlessBottom), style: {
                                              height: state.headerTierHeights[tierNum]
                                          }, children: (options.weekNumbers && rowConfig.isDateRow) ? (u$1(TimeGridWeekNumber, { dateProfile: props.dateProfile, innerWidthRef: headerLabelInnerWidthRefMap.createRef(tierNum), innerHeightRef: headerLabelInnerHeightRefMap.createRef(tierNum), width: undefined, isLiquid: true, isNarrow: cellIsNarrow })) : (u$1(TimeGridAxisEmpty, { width: undefined, isLiquid: true })) }, tierNum))) }), u$1("div", { className: generateClassName(options.slotHeaderDividerClass, {
                                          inTableHeader: true,
                                          options: { dayMinWidth: options.dayMinWidth },
                                      }) }), u$1(Scroller, { horizontal: true, hideScrollbars: true, className: joinClassNames(classNames.flexRow, classNames.liquid), ref: this.headerScrollerRef, children: [u$1("div", { role: 'rowgroup', className: canvasWidth == null ? classNames.liquid : '', style: { width: canvasWidth }, children: props.headerTiers.map((rowConfig, tierNum) => (k$1(DayGridHeaderRow, { ...rowConfig, key: tierNum, role: 'row', rowIndex: tierNum, borderBottom: tierNum < props.headerTiers.length - 1, height: state.headerTierHeights[tierNum], colWidth: appliedColWidth, viewportWidth: clientWidth, innerHeightRef: headerMainInnerHeightRefMap.createRef(tierNum), cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, rowLevel: props.headerTiers.length - tierNum - 1 }))) }), Boolean(endScrollbarWidth) && (u$1("div", { className: joinClassNames(generateClassName(options.fillerClass, { inTableHeader: true }), classNames.borderlessY, classNames.borderlessEnd), style: { minWidth: endScrollbarWidth } }))] })] }), u$1("div", { className: generateClassName(options.dayHeaderDividerClass, {
                                  isSticky: tableHeaderSticky,
                                  multiMonthColumns: 0,
                                  options: { allDaySlot: Boolean(options.allDaySlot) },
                              }) })] })), u$1("div", { role: 'rowgroup', className: joinClassNames(generateClassName(options.tableBodyClass, {
                          borderlessX,
                          borderlessTop,
                          borderlessBottom,
                          multiMonthColumns: 0,
                      }), classNames.flexCol, verticalScrolling && classNames.liquid, classNames.isolate, classNames.z0), children: [options.allDaySlot && (u$1(S, { children: [u$1("div", { role: 'row', "aria-rowindex": firstBodyRowIndex, className: joinClassNames(classNames.flexRow, classNames.z1), children: [u$1(TimeGridAllDayHeader, { width: axisWidth, innerWidthRef: this.handleAllDayLabelInnerWidth, isNarrow: cellIsNarrow }), u$1("div", { className: generateClassName(options.slotHeaderDividerClass, {
                                                  inTableHeader: false,
                                                  options: { dayMinWidth: options.dayMinWidth },
                                              }) }), u$1(Scroller, { horizontal: true, hideScrollbars: true, 
                                              // fill remaining width
                                              className: joinClassNames(classNames.flexRow, classNames.liquidX), ref: this.allDayScrollerRef, children: [u$1("div", { className: classNames.flexRow, style: { width: canvasWidth }, children: u$1(TimeGridAllDayLane, { dateProfile: props.dateProfile, todayRange: props.todayRange, cells: props.cells, showDayNumbers: false, forPrint: forPrint, isHitComboAllowed: props.isHitComboAllowed, className: joinClassNames(classNames.borderless, classNames.liquidX), cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, 
                                                          // content
                                                          fgEventSegs: props.fgEventSegs, bgEventSegs: props.bgEventSegs, businessHourSegs: props.businessHourSegs, dateSelectionSegs: props.dateSelectionSegs, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, dayMaxEvents: props.dayMaxEvents, dayMaxEventRows: props.dayMaxEventRows, 
                                                          // dimensions
                                                          colWidth: appliedColWidth }) }), Boolean(endScrollbarWidth) && (u$1("div", { className: joinClassNames(generateClassName(options.fillerClass, { inTableHeader: false }), classNames.borderlessY, classNames.borderlessEnd), style: { minWidth: endScrollbarWidth } }))] })] }), u$1("div", { className: joinClassNames(options.allDayDividerClass, classNames.z2) })] })), u$1("div", { role: 'row', "aria-rowindex": firstBodyRowIndex + (options.allDaySlot ? 1 : 0), className: joinClassNames(classNames.flexRow, classNames.rel, // for Ruler.fillStart
                              verticalScrolling && classNames.liquid, classNames.z0), children: [u$1(Scroller, { vertical: verticalScrolling, hideScrollbars: true, className: joinClassNames(classNames.flexCol, classNames.contentBox), style: {
                                          width: axisWidth,
                                      }, ref: this.axisScrollerRef, clientHeightRef: this.handleBodyHeight, children: !simplePrint && (u$1(S, { children: u$1("div", { role: 'rowheader', "aria-label": options.timedText, className: joinClassNames(classNames.flexCol, classNames.grow, classNames.rel), style: {
                                                  height: forcedBodyHeight,
                                              }, children: [u$1("div", { "aria-hidden": true, className: joinClassNames(classNames.flexCol, (verticalScrolling && options.expandRows) && classNames.grow, absPrint && classNames.fillX), children: props.slatMetas.map((slatMeta, slatI) => (k$1(TimeGridSlatHeader, { ...slatMeta /* FYI doesn't need isoTimeStr */, key: slatMeta.key, innerWidthRef: slatLabelInnerWidthRefMap.createRef(slatMeta.key), innerHeightRef: slatLabelInnerHeightRefMap.createRef(slatMeta.key), borderTop: Boolean(slatI), isNarrow: cellIsNarrow, height: slatLiquidHeight ? undefined : slatHeight, liquidHeight: slatLiquidHeight }))) }), !forPrint && options.nowIndicator && rangeContainsMarker(props.dateProfile.currentRange, nowDate) &&
                                                      nowTimeMs >= props.dateProfile.slotMinTime.milliseconds &&
                                                      nowTimeMs < props.dateProfile.slotMaxTime.milliseconds && (u$1(TimeGridNowIndicatorArrow, { nowDate: nowDate, dateProfile: props.dateProfile, totalHeight: slatHeight != null ? slatHeight * slatCnt : undefined })), Boolean(rowsNotExpanding || bottomScrollbarWidth) && (u$1("div", { className: joinClassNames(generateClassName(options.fillerClass, { inTableHeader: false }), classNames.borderlessX, classNames.borderlessBottom, rowsNotExpanding && classNames.liquid), style: {
                                                          minHeight: bottomScrollbarWidth
                                                      } }))] }) })) }), u$1("div", { className: generateClassName(options.slotHeaderDividerClass, {
                                          inTableHeader: false,
                                          options: { dayMinWidth: options.dayMinWidth },
                                      }) }), u$1("div", { 
                                      // we need this div because it's bad for Scroller to have left/right borders,
                                      // AND because we need to containt the FooterScrollbar
                                      className: joinClassNames(classNames.flexCol, classNames.liquid), children: [u$1(Scroller, { vertical: verticalScrolling, horizontal: true, hideScrollbars: footerScrollbarSticky || // also means height:auto, so won't need vertical scrollbars anyway
                                                  forPrint, className: joinClassNames(classNames.flexCol, classNames.rel, // for Ruler.fillStart
                                              verticalScrolling && classNames.liquid), ref: this.mainScrollerRef, clientWidthRef: this.handleClientWidth, clientHeightRef: this.handleClientHeight, children: u$1("div", { className: joinClassNames(classNames.flexCol, classNames.grow, classNames.rel), style: {
                                                      width: canvasWidth,
                                                      height: forcedBodyHeight,
                                                  }, children: [u$1(TimeGridCols, { dateProfile: props.dateProfile, nowDate: props.nowDate, nowMs: props.nowMs, todayRange: props.todayRange, cells: props.cells, slatCnt: slatCnt, forPrint: forPrint, isHitComboAllowed: props.isHitComboAllowed, className: simplePrint ? '' : classNames.fill, 
                                                          // content
                                                          fgEventSegsByCol: props.fgEventSegsByCol, bgEventSegsByCol: props.bgEventSegsByCol, businessHourSegsByCol: props.businessHourSegsByCol, nowIndicatorSegsByCol: props.nowIndicatorSegsByCol, dateSelectionSegsByCol: props.dateSelectionSegsByCol, eventDragByCol: props.eventDragByCol, eventResizeByCol: props.eventResizeByCol, eventSelection: props.eventSelection, 
                                                          // dimensions
                                                          colWidth: appliedColWidth, slatHeight: slatHeight, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro }), !simplePrint && (u$1(S, { children: [u$1("div", { "aria-hidden": true, className: joinClassNames(classNames.flexCol, (verticalScrolling && options.expandRows) && classNames.grow, absPrint ? classNames.fillX : classNames.rel), children: props.slatMetas.map((slatMeta, slatI) => (u$1("div", { className: joinClassNames(classNames.flexRow, slatLiquidHeight && classNames.liquid), style: {
                                                                          height: slatLiquidHeight ? '' : slatHeight
                                                                      }, children: k$1(TimeGridSlatLane, { ...slatMeta /* FYI doesn't need isoTimeStr */, key: slatMeta.key, borderTop: Boolean(slatI) }) }, slatMeta.key))) }), rowsNotExpanding && (u$1("div", { className: joinClassNames(generateClassName(options.fillerClass, { inTableHeader: false }), classNames.borderlessX, classNames.borderlessBottom, classNames.liquid) }))] }))] }) }), Boolean(footerScrollbarSticky) && (u$1(FooterScrollbar, { isSticky: true, canvasWidth: canvasWidth, scrollerRef: this.footScrollerRef, scrollbarWidthRef: this.handleStickyBottomScrollbarWidth }))] })] })] }), u$1(Ruler, { widthRef: this.handleTotalWidth })] }));
      }
      // Lifecycle
      // -----------------------------------------------------------------------------------------------
      componentDidMount() {
          this._isUnmounting = false;
          this.initScrollers();
          this.updateSlatHeight();
      }
      componentDidUpdate() {
          this.updateScrollers();
          this.updateSlatHeight();
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.destroyScrollers();
          this.prevSlatHeight = undefined;
          setRef(this.props.slatHeightRef, null);
      }
      updateSlatHeight() {
          if (this.prevSlatHeight !== this.slatHeight) {
              setRef(this.props.slatHeightRef, this.prevSlatHeight = this.slatHeight);
          }
      }
      // Scrolling
      // -----------------------------------------------------------------------------------------------
      initScrollers() {
          const ScrollerSyncer = getScrollerSyncerClass(this.context.pluginHooks);
          this.dayScroller = new ScrollerSyncer(true); // horizontal=true
          this.timeScroller = new ScrollerSyncer(); // horizontal=false
          setRef(this.props.dayScrollerRef, this.dayScroller);
          setRef(this.props.timeScrollerRef, this.timeScroller);
          this.updateScrollers();
      }
      updateScrollers() {
          this.dayScroller.handleChildren([
              this.headerScrollerRef.current,
              this.allDayScrollerRef.current,
              this.mainScrollerRef.current,
              this.footScrollerRef.current,
          ]);
          this.timeScroller.handleChildren([
              this.axisScrollerRef.current,
              this.mainScrollerRef.current,
          ]);
      }
      destroyScrollers() {
          setRef(this.props.dayScrollerRef, null);
          setRef(this.props.timeScrollerRef, null);
      }
  }
  TimeGridLayoutPannable.addPropsEquality({
      headerTierHeights: isArraysEqual,
  });

  class TimeGridLayoutNormal extends BaseComponent {
      constructor() {
          super(...arguments);
          this.state = {};
          // refs
          this.headerLabelInnerWidthRefMap = new RefMap(() => {
              afterSize(this.handleAxisInnerWidths);
          });
          this.handleAllDayLabelInnerWidth = (width) => {
              this.allDayLabelInnerWidth = width;
              afterSize(this.handleAxisInnerWidths);
          };
          this.handleWeekNumberInnerWidth = (width) => {
              this.weekNumberInnerWidth = width;
              afterSize(this.handleAxisInnerWidths);
          };
          this.slatLabelInnerWidthRefMap = new RefMap(() => {
              afterSize(this.handleAxisInnerWidths);
          });
          this.slatLabelInnerHeightRefMap = new RefMap(() => {
              afterSize(this.handleSlatInnerHeights);
          });
          // Sizing
          // -----------------------------------------------------------------------------------------------
          this.handleTotalWidth = (totalWidth) => {
              if (this._isUnmounting)
                  return;
              // Must delay the rerender because might change the width of the all-day DayGridRow events,
              // which shows a ResizeObserver loop warning
              requestAnimationFrame(() => {
                  if (this._isUnmounting)
                      return;
                  this.setState({ totalWidth });
              });
          };
          this.handleClientWidth = (clientWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ clientWidth });
          };
          this.handleClientHeight = (clientHeight) => {
              if (this._isUnmounting)
                  return;
              this.setState({ clientHeight });
          };
          this.handleAxisInnerWidths = () => {
              if (this._isUnmounting)
                  return;
              const headerLabelInnerWidthMap = this.headerLabelInnerWidthRefMap.current;
              const slatLabelInnerWidthMap = this.slatLabelInnerWidthRefMap.current;
              let max = Math.max(this.weekNumberInnerWidth || 0, // might not exist
              this.allDayLabelInnerWidth || 0 // guard against all-day slot hidden
              );
              for (const headerLabelInnerWidth of headerLabelInnerWidthMap.values()) {
                  max = Math.max(max, headerLabelInnerWidth);
              }
              for (const slatLabelInnerWidth of slatLabelInnerWidthMap.values()) {
                  max = Math.max(max, slatLabelInnerWidth);
              }
              if (this.state.axisWidth !== max) {
                  this.setState({ axisWidth: max });
              }
          };
          this.handleSlatInnerHeights = () => {
              if (this._isUnmounting)
                  return;
              const slatLabelInnerHeightMap = this.slatLabelInnerHeightRefMap.current;
              let max = 0;
              for (const slatLabelInnerHeight of slatLabelInnerHeightMap.values()) {
                  max = Math.max(max, slatLabelInnerHeight);
              }
              if (this.state.slatInnerHeight !== max) {
                  this.setState({ slatInnerHeight: max });
              }
          };
      }
      render() {
          const { props, state, context, slatLabelInnerWidthRefMap, slatLabelInnerHeightRefMap, headerLabelInnerWidthRefMap } = this;
          const { nowDate, forPrint } = props;
          const nowTimeMs = nowDate.valueOf() - startOfDay(nowDate).valueOf();
          const { axisWidth, clientWidth, totalWidth } = state;
          const { options } = context;
          const { borderlessX, borderlessTop, borderlessBottom } = computeViewBorderless(options);
          const endScrollbarWidth = (totalWidth != null && clientWidth != null && !forPrint)
              ? totalWidth - clientWidth
              : undefined;
          const verticalScrolling = !forPrint && !getIsHeightAuto(options);
          const tableHeaderSticky = !forPrint && getTableHeaderSticky(options);
          const slatCnt = props.slatMetas.length;
          const [slatHeight, slatLiquidHeight] = computeSlatHeight(verticalScrolling && options.expandRows, slatCnt, options.slotMinHeight, state.slatInnerHeight, state.clientHeight);
          this.slatHeight = slatHeight;
          // TODO: have computeSlatHeight return?
          const totalSlatHeight = (slatHeight || 0) * slatCnt;
          const rowsNotExpanding = verticalScrolling && !options.expandRows &&
              state.clientHeight != null && state.clientHeight > totalSlatHeight;
          const printStackEnabled = computeTimeGridPrintMode(forPrint, options.eventPrintLayout) === 'stack';
          const absPrint = forPrint && !printStackEnabled;
          const simplePrint = forPrint && printStackEnabled;
          // for printing
          // in Chrome, slats and columns both need abs positioning within a relative container for them
          // to sync across pages, and the relative container needs an explicit height
          // in Firefox, same applies, but the flex-row for the cells has trouble spanning across page,
          // so we need to set explicit height on flex-row and all parents
          const forcedBodyHeight = absPrint ? totalSlatHeight : undefined;
          const colCount = props.cells.length;
          const measuredColWidth = clientWidth != null ? clientWidth / colCount : undefined;
          const cellIsMicro = measuredColWidth != null && measuredColWidth <= dayMicroWidth;
          const cellIsNarrow = cellIsMicro || (measuredColWidth != null && measuredColWidth <= options.dayNarrowWidth);
          return (u$1(S, { children: [options.dayHeaders && (u$1("div", { role: 'rowgroup', className: joinClassNames(generateClassName(options.tableHeaderClass, {
                          isSticky: tableHeaderSticky,
                          borderlessX,
                          borderlessTop,
                          borderlessBottom,
                          multiMonthColumns: 0,
                      }), 
                      // See the note in TimeGridLayout about why print doesn't use repeating headers.
                      classNames.flexCol, tableHeaderSticky && classNames.tableHeaderSticky, classNames.z1), children: [props.headerTiers.map((rowConfig, tierNum) => (u$1("div", { role: 'row', className: classNames.flexRow, children: [u$1("div", { className: joinClassNames(options.dayHeaderRowClass, classNames.flexRow, classNames.borderlessX, classNames.borderlessTop, tierNum === props.headerTiers.length - 1 && classNames.borderlessBottom), children: (options.weekNumbers && rowConfig.isDateRow) ? (u$1(TimeGridWeekNumber, { dateProfile: props.dateProfile, innerWidthRef: this.handleWeekNumberInnerWidth, innerHeightRef: headerLabelInnerWidthRefMap.createRef(tierNum), width: axisWidth, isLiquid: false, isNarrow: cellIsNarrow })) : (u$1(TimeGridAxisEmpty, { width: axisWidth, isLiquid: false })) }), u$1("div", { className: generateClassName(options.slotHeaderDividerClass, {
                                          inTableHeader: true,
                                          options: { dayMinWidth: options.dayMinWidth },
                                      }) }), u$1(DayGridHeaderRow, { ...rowConfig, className: classNames.liquid, borderBottom: tierNum < props.headerTiers.length - 1, viewportWidth: clientWidth, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, rowLevel: props.headerTiers.length - tierNum - 1 }), Boolean(endScrollbarWidth) && (u$1("div", { className: joinClassNames(generateClassName(options.fillerClass, { inTableHeader: true }), classNames.borderlessY, classNames.borderlessEnd), style: { minWidth: endScrollbarWidth } }))] }, tierNum))), u$1("div", { className: generateClassName(options.dayHeaderDividerClass, {
                                  isSticky: tableHeaderSticky,
                                  multiMonthColumns: 0,
                                  options: { allDaySlot: Boolean(options.allDaySlot) },
                              }) })] })), u$1("div", { role: 'rowgroup', className: joinClassNames(generateClassName(options.tableBodyClass, {
                          borderlessX,
                          borderlessTop,
                          borderlessBottom,
                          multiMonthColumns: 0,
                      }), classNames.flexCol, verticalScrolling && classNames.liquid, classNames.isolate, classNames.z0), children: [options.allDaySlot && (u$1(S, { children: [u$1("div", { role: 'row', className: joinClassNames(classNames.flexRow, classNames.z1), children: [u$1(TimeGridAllDayHeader, { width: axisWidth, innerWidthRef: this.handleAllDayLabelInnerWidth, isNarrow: cellIsNarrow }), u$1("div", { className: generateClassName(options.slotHeaderDividerClass, {
                                                  inTableHeader: false,
                                                  options: { dayMinWidth: options.dayMinWidth },
                                              }) }), u$1(TimeGridAllDayLane, { dateProfile: props.dateProfile, todayRange: props.todayRange, cells: props.cells, showDayNumbers: false, forPrint: forPrint, isHitComboAllowed: props.isHitComboAllowed, className: joinClassNames(classNames.liquidX, classNames.borderless), cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, 
                                              // content
                                              fgEventSegs: props.fgEventSegs, bgEventSegs: props.bgEventSegs, businessHourSegs: props.businessHourSegs, dateSelectionSegs: props.dateSelectionSegs, eventDrag: props.eventDrag, eventResize: props.eventResize, eventSelection: props.eventSelection, dayMaxEvents: props.dayMaxEvents, dayMaxEventRows: props.dayMaxEventRows }), Boolean(endScrollbarWidth) && (u$1("div", { className: joinClassNames(generateClassName(options.fillerClass, { inTableHeader: false }), classNames.borderlessY, classNames.borderlessEnd), style: { minWidth: endScrollbarWidth } }))] }), u$1("div", { className: joinClassNames(options.allDayDividerClass, classNames.z2) })] })), u$1(Scroller, { vertical: verticalScrolling, className: joinClassNames(classNames.flexCol, classNames.rel, // for Ruler.fillStart
                              verticalScrolling && classNames.liquid, classNames.z0), ref: props.timeScrollerRef, clientWidthRef: this.handleClientWidth, clientHeightRef: this.handleClientHeight, children: u$1("div", { className: joinClassNames(classNames.flexCol, classNames.grow, classNames.rel), style: {
                                      // in print mode, this div creates the height and everything is absolutely positioned within
                                      // we need to do this so that slats positioning synces with events's positioning
                                      // otherwise, get out of sync on second page
                                      height: forcedBodyHeight,
                                  }, children: [u$1("div", { role: 'row', className: joinClassNames(classNames.flexRow, !simplePrint && classNames.fill), children: [u$1("div", { role: 'rowheader', "aria-label": options.timedText, className: classNames.contentBox, style: { width: axisWidth } }), u$1("div", { className: generateClassName(options.slotHeaderDividerClass, {
                                                      inTableHeader: false,
                                                      options: { dayMinWidth: options.dayMinWidth },
                                                  }) }), u$1(TimeGridCols, { dateProfile: props.dateProfile, nowDate: props.nowDate, nowMs: props.nowMs, todayRange: props.todayRange, cells: props.cells, slatCnt: slatCnt, forPrint: forPrint, isHitComboAllowed: props.isHitComboAllowed, className: classNames.liquid, 
                                                  // content
                                                  fgEventSegsByCol: props.fgEventSegsByCol, bgEventSegsByCol: props.bgEventSegsByCol, businessHourSegsByCol: props.businessHourSegsByCol, nowIndicatorSegsByCol: props.nowIndicatorSegsByCol, dateSelectionSegsByCol: props.dateSelectionSegsByCol, eventDragByCol: props.eventDragByCol, eventResizeByCol: props.eventResizeByCol, eventSelection: props.eventSelection, 
                                                  // dimensions
                                                  slatHeight: slatHeight, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro })] }), !simplePrint && (u$1(S, { children: [u$1("div", { "aria-hidden": true, className: joinClassNames(classNames.flexCol, (verticalScrolling && options.expandRows) && classNames.grow, absPrint
                                                      ? classNames.fillX // will assume top:0, height will be decided naturally
                                                      : classNames.rel), children: props.slatMetas.map((slatMeta, slatI) => (u$1("div", { className: joinClassNames(slatLiquidHeight && classNames.liquid, classNames.flexRow), style: {
                                                          height: slatLiquidHeight ? undefined : slatHeight
                                                      }, children: [u$1("div", { 
                                                              // the pannable version of TimeGrid has axis labels all consecutive in one column
                                                              // simulate this for the non-pannable version
                                                              className: classNames.flexCol, style: { width: axisWidth }, children: k$1(TimeGridSlatHeader, { ...slatMeta /* FYI doesn't need isoTimeStr */, key: slatMeta.key, innerWidthRef: slatLabelInnerWidthRefMap.createRef(slatMeta.key), innerHeightRef: slatLabelInnerHeightRefMap.createRef(slatMeta.key), borderTop: Boolean(slatI), isNarrow: cellIsNarrow }) }), u$1("div", { className: generateClassName(options.slotHeaderDividerClass, {
                                                                  inTableHeader: false,
                                                                  options: { dayMinWidth: options.dayMinWidth },
                                                              }), style: { visibility: 'hidden' } }), k$1(TimeGridSlatLane, { ...slatMeta /* FYI doesn't need isoTimeStr */, key: slatMeta.key, borderTop: Boolean(slatI) })] }, slatMeta.key))) }), rowsNotExpanding && (u$1("div", { className: joinClassNames(generateClassName(options.fillerClass, { inTableHeader: false }), classNames.borderlessX, classNames.borderlessBottom, classNames.liquid) })), !forPrint && options.nowIndicator && rangeContainsMarker(props.dateProfile.currentRange, nowDate) &&
                                                  nowTimeMs >= props.dateProfile.slotMinTime.milliseconds &&
                                                  nowTimeMs < props.dateProfile.slotMaxTime.milliseconds && (u$1(TimeGridNowIndicatorArrow, { nowDate: nowDate, dateProfile: props.dateProfile, totalHeight: slatHeight != null ? slatHeight * slatCnt : undefined }))] }))] }) })] }), u$1(Ruler, { widthRef: this.handleTotalWidth })] }));
      }
      // Lifecycle
      // -----------------------------------------------------------------------------------------------
      componentDidMount() {
          this._isUnmounting = false;
          this.updateSlatHeight();
      }
      componentDidUpdate() {
          this.updateSlatHeight();
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.prevSlatHeight = undefined;
          setRef(this.props.slatHeightRef, null);
      }
      updateSlatHeight() {
          if (this.prevSlatHeight !== this.slatHeight) {
              setRef(this.props.slatHeightRef, this.prevSlatHeight = this.slatHeight);
          }
      }
  }

  function buildEmptySegCols(segsByCol) {
      return segsByCol.map(() => []);
  }
  function buildEmptyInteractionCols(interactionsByCol) {
      return interactionsByCol.map(() => null);
  }
  class TimeGridLayout extends BaseComponent {
      constructor() {
          super(...arguments);
          // memo
          this.buildSlatMetas = memoize(buildSlatMetas);
          // refs
          this.dayScrollerRef = M$1();
          this.timeScrollerRef = M$1();
          this.scrollState = {}; // updated in-place
          // Sizing
          // -----------------------------------------------------------------------------------------------
          this.handleSlatHeight = (slatHeight) => {
              if (this._isUnmounting)
                  return;
              this.slatHeight = slatHeight;
              if (slatHeight != null) {
                  afterSize(this.applyTimeScroll);
              }
          };
          this.handleTimeScrollRequest = (scrollTime) => {
              this.scrollState.time = scrollTime;
              this.scrollState.y = undefined;
              this.applyTimeScroll();
          };
          /*
          Captures current values
          */
          this.handleTimeScrollEnd = (isDevice) => {
              if (isDevice) {
                  const y = this.timeScrollerRef.current.y;
                  // record, but only if not forPrint, which could give bogus values in the case of
                  // TimeGridLayoutPannable, which kills y-scrolling, but retains x-scrolling,
                  // which reports as a 0 y-scroll.
                  if (!this.props.forPrint) {
                      this.scrollState.y = y;
                      this.scrollState.time = undefined;
                  }
              }
          };
          this.applyTimeScroll = () => {
              const timeScroller = this.timeScrollerRef.current;
              const { slatHeight, scrollState } = this;
              let { y, time } = scrollState;
              if (y == null &&
                  time &&
                  slatHeight != null &&
                  // Since applyTimeScroll is called by handleSlatHeight, could be called with null during cleanup,
                  // and the timeScroller might not exist
                  timeScroller) {
                  y = computeTimeTopFrac(time, this.props.dateProfile)
                      * (slatHeight * this.currentSlatCnt);
                  if (y) {
                      y++; // overcome top border
                  }
                  scrollState.y = y; // HACK: store raw pixel value
              }
              if (y != null) {
                  timeScroller.scrollTo({ y });
              }
          };
      }
      render() {
          const { props, context } = this;
          const { dateProfile } = props;
          const { options, dateEnv } = context;
          const { dayMinWidth } = options;
          const { borderlessX, borderlessTop, borderlessBottom } = computeViewBorderless(options);
          const slatMetas = this.buildSlatMetas(dateProfile.slotMinTime, dateProfile.slotMaxTime, options.slotHeaderInterval, options.slotDuration, dateEnv);
          this.currentSlatCnt = slatMetas.length;
          const dateSelectionSegs = props.forPrint ? [] : props.dateSelectionSegs;
          const eventDrag = props.forPrint ? null : props.eventDrag;
          const eventResize = props.forPrint ? null : props.eventResize;
          const dateSelectionSegsByCol = props.forPrint ? buildEmptySegCols(props.dateSelectionSegsByCol) : props.dateSelectionSegsByCol;
          const eventDragByCol = props.forPrint ? buildEmptyInteractionCols(props.eventDragByCol) : props.eventDragByCol;
          const eventResizeByCol = props.forPrint ? buildEmptyInteractionCols(props.eventResizeByCol) : props.eventResizeByCol;
          const commonLayoutProps = {
              dateProfile: dateProfile,
              nowDate: props.nowDate,
              nowMs: props.nowMs,
              todayRange: props.todayRange,
              cells: props.cells,
              slatMetas,
              forPrint: props.forPrint,
              isHitComboAllowed: props.isHitComboAllowed,
              // header content
              headerTiers: props.headerTiers,
              // all-day content
              fgEventSegs: props.fgEventSegs,
              bgEventSegs: props.bgEventSegs,
              businessHourSegs: props.businessHourSegs,
              dateSelectionSegs,
              eventDrag,
              eventResize,
              ...getAllDayMaxEventProps(options),
              // timed content
              fgEventSegsByCol: props.fgEventSegsByCol,
              bgEventSegsByCol: props.bgEventSegsByCol,
              businessHourSegsByCol: props.businessHourSegsByCol,
              nowIndicatorSegsByCol: props.nowIndicatorSegsByCol,
              dateSelectionSegsByCol,
              eventDragByCol,
              eventResizeByCol,
              // universal content
              eventSelection: props.eventSelection,
              // refs
              timeScrollerRef: this.timeScrollerRef,
              timeScrollState: this.scrollState,
              slatHeightRef: this.handleSlatHeight,
              borderlessX,
              borderlessBottom,
          };
          return (u$1(ViewContainer, { attrs: {
                  role: 'grid',
                  'aria-colcount': props.cells.length,
                  'aria-labelledby': props.labelId,
                  'aria-label': props.labelStr,
              }, className: joinClassNames(props.className, generateClassName(options.tableClass, {
                  borderlessX,
                  borderlessTop,
                  borderlessBottom,
                  multiMonthColumns: 0,
              }), 
              // We don't use the repeating-header print treatment here because it works poorly:
              // - Firefox >85ish CAN have flexboxes within it, but those cannot do absolute positioning
              // - Chrome works okay, but abs-positioned events cover the repeated header
              //   Also, there's weird padding on the last page at bottom of container, which matches
              //   the height of the repeated header
              // - Safari was never able to do repeated headers in the first place
              !props.forPrint && classNames.flexCol, classNames.isolate), viewSpec: context.viewSpec, children: dayMinWidth ? (u$1(TimeGridLayoutPannable, { ...commonLayoutProps, dayMinWidth: dayMinWidth, dayScrollerRef: this.dayScrollerRef })) : (u$1(TimeGridLayoutNormal, { ...commonLayoutProps })) }));
      }
      // Lifecycle
      // -----------------------------------------------------------------------------------------------
      componentDidMount() {
          this._isUnmounting = false;
          this.resetScroll();
          this.context.emitter.on('_timeScrollRequest', this.handleTimeScrollRequest);
          const timeScroller = this.timeScrollerRef.current;
          if (timeScroller) {
              timeScroller.addScrollEndListener(this.handleTimeScrollEnd);
          }
      }
      componentDidUpdate(prevProps) {
          if (prevProps.dateProfile !== this.props.dateProfile && this.context.options.scrollTimeReset) {
              this.resetScroll();
          }
          else if (prevProps.forPrint && !this.props.forPrint) {
              // returning from print
              // reapply scrolling because scroll-divs were probably restored
              this.applyTimeScroll();
          }
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.context.emitter.off('_timeScrollRequest', this.handleTimeScrollRequest);
          const timeScroller = this.timeScrollerRef.current;
          if (timeScroller) {
              timeScroller.removeScrollEndListener(this.handleTimeScrollEnd);
          }
      }
      // Scrolling
      // -----------------------------------------------------------------------------------------------
      resetScroll() {
          this.handleTimeScrollRequest(this.context.options.scrollTime);
          // also resets day scroll
          const dayScroller = this.dayScrollerRef.current;
          if (dayScroller) {
              dayScroller.scrollTo({ x: 0 });
          }
      }
  }
  // Utils
  // -----------------------------------------------------------------------------------------------
  const AUTO_ALL_DAY_MAX_EVENT_ROWS = 5;
  function getAllDayMaxEventProps(options) {
      let { dayMaxEvents, dayMaxEventRows } = options;
      if (dayMaxEvents === true || dayMaxEventRows === true) { // is auto?
          dayMaxEvents = undefined;
          dayMaxEventRows = AUTO_ALL_DAY_MAX_EVENT_ROWS; // make sure "auto" goes to a real number
      }
      return { dayMaxEvents, dayMaxEventRows };
  }

  /*
  An abstraction for a dragging interaction originating on an event.
  Does higher-level things than PointerDragger, such as possibly:
  - a "mirror" that moves with the pointer
  - a minimum number of pixels or other criteria for a true drag to begin

  subclasses must emit:
  - pointerdown
  - dragstart
  - dragmove
  - pointerup
  - dragend
  */
  class ElementDragging {
      constructor(el, selector) {
          this.emitter = new Emitter();
      }
      destroy() {
      }
      setMirrorIsVisible(bool) {
          // optional if subclass doesn't want to support a mirror
      }
      setMirrorNeedsRevert(bool) {
          // optional if subclass doesn't want to support a mirror
      }
      setAutoScrollEnabled(bool) {
          // optional
      }
  }

  // TODO: get rid of this in favor of options system,
  // tho it's really easy to access this globally rather than pass thru options.
  const config = {};

  // high-level segmenting-aware tester functions
  // ------------------------------------------------------------------------------------------------------------------------
  function isInteractionValid(interaction, dateProfile, context) {
      let { instances } = interaction.mutatedEvents;
      for (let instanceId in instances) {
          if (!rangeContainsRange(dateProfile.validRange, instances[instanceId].range)) {
              return false;
          }
      }
      return isNewPropsValid({ eventDrag: interaction }, context); // HACK: the eventDrag props is used for ALL interactions
  }
  function isDateSelectionValid(dateSelection, dateProfile, context) {
      if (!rangeContainsRange(dateProfile.validRange, dateSelection.range)) {
          return false;
      }
      return isNewPropsValid({ dateSelection }, context);
  }
  function isNewPropsValid(newProps, context) {
      let calendarState = context.getCurrentData();
      let props = {
          businessHours: calendarState.businessHours,
          dateSelection: '',
          eventStore: calendarState.eventStore,
          eventUiBases: calendarState.eventUiBases,
          eventSelection: '',
          eventDrag: null,
          eventResize: null,
          ...newProps,
      };
      return (context.pluginHooks.isPropsValid || isPropsValid)(props, context);
  }
  function isPropsValid(state, context, dateSpanMeta = {}, filterConfig) {
      if (state.eventDrag && !isInteractionPropsValid(state, context, dateSpanMeta, filterConfig)) {
          return false;
      }
      if (state.dateSelection && !isDateSelectionPropsValid(state, context, dateSpanMeta, filterConfig)) {
          return false;
      }
      return true;
  }
  // Moving Event Validation
  // ------------------------------------------------------------------------------------------------------------------------
  function isInteractionPropsValid(state, context, dateSpanMeta, filterConfig) {
      let currentState = context.getCurrentData();
      let interaction = state.eventDrag; // HACK: the eventDrag props is used for ALL interactions
      let subjectEventStore = interaction.mutatedEvents;
      let subjectDefs = subjectEventStore.defs;
      let subjectInstances = subjectEventStore.instances;
      let subjectConfigs = compileEventUis(subjectDefs, interaction.isEvent ?
          state.eventUiBases :
          { '': currentState.selectionConfig });
      if (filterConfig) {
          subjectConfigs = mapHash(subjectConfigs, filterConfig);
      }
      // exclude the subject events. TODO: exclude defs too?
      let otherEventStore = excludeInstances(state.eventStore, interaction.affectedEvents.instances);
      let otherDefs = otherEventStore.defs;
      let otherInstances = otherEventStore.instances;
      let otherConfigs = compileEventUis(otherDefs, state.eventUiBases);
      for (let subjectInstanceId in subjectInstances) {
          let subjectInstance = subjectInstances[subjectInstanceId];
          let subjectRange = subjectInstance.range;
          let subjectConfig = subjectConfigs[subjectInstance.defId];
          let subjectDef = subjectDefs[subjectInstance.defId];
          // constraint
          if (!allConstraintsPass(subjectConfig.constraints, subjectRange, otherEventStore, state.businessHours, context)) {
              return false;
          }
          // overlap
          let { eventOverlap } = context.options;
          let eventOverlapFunc = typeof eventOverlap === 'function' ? eventOverlap : null;
          for (let otherInstanceId in otherInstances) {
              let otherInstance = otherInstances[otherInstanceId];
              // intersect! evaluate (exact-instant-aware: fold-compressed civil readings must
              // not falsely collide across the two passes of a repeated hour)
              if (instanceRangesIntersect(subjectRange, otherInstance.range, context.dateEnv)) {
                  let otherOverlap = otherConfigs[otherInstance.defId].overlap;
                  // consider the other event's overlap. only do this if the subject event is a "real" event
                  if (otherOverlap === false && interaction.isEvent) {
                      return false;
                  }
                  if (subjectConfig.overlap === false) {
                      return false;
                  }
                  if (eventOverlapFunc && !eventOverlapFunc(new EventImpl(context, otherDefs[otherInstance.defId], otherInstance), // still event
                  new EventImpl(context, subjectDef, subjectInstance))) {
                      return false;
                  }
              }
          }
          // allow (a function)
          let calendarEventStore = currentState.eventStore; // need global-to-calendar, not local to component (splittable)state
          for (let subjectAllow of subjectConfig.allows) {
              let subjectDateSpan = {
                  ...dateSpanMeta,
                  range: subjectInstance.range,
                  allDay: subjectDef.allDay,
              };
              let origDef = calendarEventStore.defs[subjectDef.defId];
              let origInstance = calendarEventStore.instances[subjectInstanceId];
              let eventApi;
              if (origDef) { // was previously in the calendar
                  eventApi = new EventImpl(context, origDef, origInstance);
              }
              else { // was an external event
                  eventApi = new EventImpl(context, subjectDef); // no instance, because had no dates
              }
              if (!subjectAllow(buildDateSpanApiWithContext(subjectDateSpan, context), eventApi)) {
                  return false;
              }
          }
      }
      return true;
  }
  // Date Selection Validation
  // ------------------------------------------------------------------------------------------------------------------------
  function isDateSelectionPropsValid(state, context, dateSpanMeta, filterConfig) {
      let relevantEventStore = state.eventStore;
      let relevantDefs = relevantEventStore.defs;
      let relevantInstances = relevantEventStore.instances;
      let selection = state.dateSelection;
      // carry the span's exact instants (stamped by instant-aware views) into range checks
      let selectionRange = buildEventInstanceRange(selection.range.start, selection.range.end, selection.instantStartMs, selection.instantEndMs);
      let { selectionConfig } = context.getCurrentData();
      if (filterConfig) {
          selectionConfig = filterConfig(selectionConfig);
      }
      // constraint
      if (!allConstraintsPass(selectionConfig.constraints, selectionRange, relevantEventStore, state.businessHours, context)) {
          return false;
      }
      // overlap
      let { selectOverlap } = context.options;
      let selectOverlapFunc = typeof selectOverlap === 'function' ? selectOverlap : null;
      for (let relevantInstanceId in relevantInstances) {
          let relevantInstance = relevantInstances[relevantInstanceId];
          // intersect! evaluate
          if (instanceRangesIntersect(selectionRange, relevantInstance.range, context.dateEnv)) {
              if (selectionConfig.overlap === false) {
                  return false;
              }
              if (selectOverlapFunc && !selectOverlapFunc(new EventImpl(context, relevantDefs[relevantInstance.defId], relevantInstance), null)) {
                  return false;
              }
          }
      }
      // allow (a function)
      for (let selectionAllow of selectionConfig.allows) {
          let fullDateSpan = { ...dateSpanMeta, ...selection };
          if (!selectionAllow(buildDateSpanApiWithContext(fullDateSpan, context), null)) {
              return false;
          }
      }
      return true;
  }
  // Constraint Utils
  // ------------------------------------------------------------------------------------------------------------------------
  function allConstraintsPass(constraints, subjectRange, otherEventStore, businessHoursUnexpanded, context) {
      for (let constraint of constraints) {
          if (!anyRangesContainRange(constraintToRanges(constraint, subjectRange, otherEventStore, businessHoursUnexpanded, context), subjectRange, context)) {
              return false;
          }
      }
      return true;
  }
  function constraintToRanges(constraint, subjectRange, // for expanding a recurring constraint, or expanding business hours
  otherEventStore, // for if constraint is an even group ID
  businessHoursUnexpanded, // for if constraint is 'businessHours'
  context) {
      if (constraint === 'businessHours') {
          return eventStoreToRanges(expandRecurring(businessHoursUnexpanded, subjectRange, context));
      }
      if (typeof constraint === 'string') { // an group ID
          return eventStoreToRanges(filterEventStoreDefs(otherEventStore, (eventDef) => eventDef.groupId === constraint));
      }
      if (typeof constraint === 'object' && constraint) { // non-null object
          return eventStoreToRanges(expandRecurring(constraint, subjectRange, context));
      }
      return []; // if it's false
  }
  // TODO: move to event-store file?
  function eventStoreToRanges(eventStore) {
      let { instances } = eventStore;
      let ranges = [];
      for (let instanceId in instances) {
          ranges.push(instances[instanceId].range);
      }
      return ranges;
  }
  // TODO: move to geom file?
  function anyRangesContainRange(outerRanges, innerRange, context) {
      for (let outerRange of outerRanges) {
          if (instanceRangeContainsRange(outerRange, innerRange, context.dateEnv)) {
              return true;
          }
      }
      return false;
  }

  function debounce(fn, ms) {
      let timeoutStarted;
      let timeoutAdded;
      let timeoutId; // thruthiness indicates whether active timeout
      function runWithTimeout(timeout) {
          timeoutStarted = Date.now();
          timeoutAdded = 0;
          timeoutId = setTimeout(() => {
              if (timeoutAdded) {
                  runWithTimeout(timeoutAdded);
              }
              else {
                  timeoutId = undefined;
                  fn();
              }
          }, timeout);
      }
      function request() {
          if (timeoutId) {
              timeoutAdded = Date.now() - timeoutStarted;
          }
          else {
              runWithTimeout(ms);
          }
      }
      function cancel() {
          if (timeoutId) {
              clearTimeout(timeoutId);
              timeoutId = undefined;
          }
      }
      return [request, cancel];
  }

  class Store {
      constructor() {
          this.handlers = [];
      }
      set(value) {
          this.currentValue = value;
          for (let handler of this.handlers) {
              handler(value);
          }
      }
      subscribe(handler) {
          this.handlers.push(handler);
          if (this.currentValue !== undefined) {
              handler(this.currentValue);
          }
      }
  }

  /*
  Subscribers will get a LIST of CustomRenderings
  */
  class CustomRenderingStore extends Store {
      constructor() {
          super(...arguments);
          this.map = new Map();
      }
      // for consistent order
      handle(customRendering) {
          const { map } = this;
          let updated = false;
          if (customRendering.isActive) {
              map.set(customRendering.id, customRendering);
              updated = true;
          }
          else if (map.has(customRendering.id)) {
              map.delete(customRendering.id);
              updated = true;
          }
          if (updated) {
              this.set(map);
          }
      }
  }

  var protectedApi = /*#__PURE__*/Object.freeze({
      __proto__: null,
      CustomRenderingStore: CustomRenderingStore,
      debounce: debounce,
      EventImpl: EventImpl,
      buildEventRangeKey: buildEventRangeKey,
      buildValidInstanceRange: buildValidInstanceRange,
      combineEventUis: combineEventUis,
      compareByFieldSpecs: compareByFieldSpecs,
      computeViewBorderless: computeViewBorderless,
      computeVisibleDayRange: computeVisibleDayRange,
      createEventUi: createEventUi,
      createFormatter: createFormatter,
      filterHash: filterHash,
      flexibleCompare: flexibleCompare,
      getDateSpanInstantEndMs: getDateSpanInstantEndMs,
      getDateSpanInstantStartMs: getDateSpanInstantStartMs,
      getEventRangeMeta: getEventRangeMeta,
      getRangeInstantEndMs: getRangeInstantEndMs,
      getRangeInstantStartMs: getRangeInstantStartMs,
      guid: guid,
      identity: identity,
      isArraysEqual: isArraysEqual,
      isPropsEqualShallow: isPropsEqualShallow,
      mapHash: mapHash,
      mergeEventStores: mergeEventStores,
      parseFieldSpecs: parseFieldSpecs,
      refineClassName: refineClassName,
      refineClassNameGenerator: refineClassNameGenerator,
      refineProps: refineProps,
      removeExact: removeExact,
      sortEventSegs: sortEventSegs,
      warn: warn,
      CalendarApiImpl: CalendarApiImpl,
      CalendarDataManager: CalendarDataManager,
      CalendarInner: CalendarInner,
      CalendarMediaRoot: CalendarMediaRoot,
      computeRootClassName: computeRootClassName,
      parseBusinessHours: parseBusinessHours,
      BaseComponent: BaseComponent,
      ContentContainer: ContentContainer,
      RenderId: RenderId,
      afterSize: afterSize,
      generateClassName: generateClassName,
      getFooterScrollbarSticky: getFooterScrollbarSticky,
      getIsHeightAuto: getIsHeightAuto,
      getTableHeaderSticky: getTableHeaderSticky,
      memoize: memoize,
      memoizeObjArg: memoizeObjArg,
      setRef: setRef,
      watchHeight: watchHeight,
      watchSize: watchSize,
      watchWidth: watchWidth,
      computeEdges: computeEdges,
      computeInnerRect: computeInnerRect,
      getRectCenter: getRectCenter,
      joinFuncishClassNames: joinFuncishClassNames,
      mergeCalendarOptions: mergeCalendarOptions,
      mergeContentInjectors: mergeContentInjectors,
      mergeLifecycleCallbacks: mergeLifecycleCallbacks,
      mergeViewOptionsMap: mergeViewOptionsMap,
      applyStyleProp: applyStyleProp,
      computeElIsRtl: computeElIsRtl,
      AllDaySplitter: AllDaySplitter,
      DayTimeColsSlicer: DayTimeColsSlicer,
      NowIndicatorDot: NowIndicatorDot,
      NowIndicatorHeaderContainer: NowIndicatorHeaderContainer,
      NowIndicatorLineContainer: NowIndicatorLineContainer,
      Splitter: Splitter,
      TimeGridLayout: TimeGridLayout,
      buildDayCols: buildDayCols,
      buildDayColsFromSeries: buildDayColsFromSeries,
      organizeSegsByCol: organizeSegsByCol,
      splitInteractionByCol: splitInteractionByCol,
      DateComponent: DateComponent,
      DelayedRunner: DelayedRunner,
      NowTimer: NowTimer,
      Scroller: Scroller,
      StandardEvent: StandardEvent,
      ViewContainer: ViewContainer,
      buildNavLinkAttrs: buildNavLinkAttrs,
      getDateMeta: getDateMeta,
      requestJson: requestJson,
      unpromisify: unpromisify,
      Emitter: Emitter,
      DateProfileGenerator: DateProfileGenerator,
      computeMajorUnit: computeMajorUnit,
      isMajorUnit: isMajorUnit,
      BgEvent: BgEvent,
      DEFAULT_UNMEASURED_EVENT_THICKNESS: DEFAULT_UNMEASURED_EVENT_THICKNESS,
      DaySeriesModel: DaySeriesModel,
      DaySeriesSlicer: DaySeriesSlicer,
      DayTableModel: DayTableModel,
      DayTableSlicer: DayTableSlicer,
      MeasuredHeightHarness: MeasuredHeightHarness,
      MoreLinkContainer: MoreLinkContainer,
      RefMap: RefMap,
      Ruler: Ruler,
      Slicer: Slicer,
      buildDateDataConfigs: buildDateDataConfigs,
      buildDateRenderConfig: buildDateRenderConfig,
      buildDateRowConfig: buildDateRowConfig,
      buildDayTableModel: buildDayTableModel,
      buildLevelLimitedLayout: buildLevelLimitedLayout,
      buildPrintEventBands: buildPrintEventBands,
      buildPrintMoreLinkBand: buildPrintMoreLinkBand,
      computeLateralSpanBottom: computeLateralSpanBottom,
      createDayHeaderFormatter: createDayHeaderFormatter,
      getSliceKey: getSliceKey,
      groupLaterallyIntersecting: groupLaterallyIntersecting,
      planPrintDomCandidates: planPrintDomCandidates,
      renderFill: renderFill,
      sortByAxisOrder: sortByAxisOrder,
      ElementDragging: ElementDragging,
      config: config,
      isPropsValid: isPropsValid,
      DayGridLayout: DayGridLayout,
      FooterScrollbar: FooterScrollbar,
      DateEnv: DateEnv,
      addDays: addDays,
      addMs: addMs,
      asCleanDays: asCleanDays,
      asRoughMinutes: asRoughMinutes,
      asRoughMs: asRoughMs,
      asRoughSeconds: asRoughSeconds,
      createDuration: createDuration,
      diffDayAndTime: diffDayAndTime,
      diffWholeDays: diffWholeDays,
      diffWholeWeeks: diffWholeWeeks,
      formatDayString: formatDayString,
      greatestDurationDenominator: greatestDurationDenominator,
      intersectRanges: intersectRanges,
      isInt: isInt,
      isValidDate: isValidDate,
      multiplyDuration: multiplyDuration,
      padStart: padStart,
      parseMarker: parse,
      rangeContainsMarker: rangeContainsMarker,
      rangesEqual: rangesEqual,
      rangesIntersect: rangesIntersect,
      startOfDay: startOfDay,
      wholeDivideDurations: wholeDivideDurations
  });

  config.touchMouseIgnoreWait = 500;
  let ignoreMouseDepth = 0;
  let listenerCnt = 0;
  let isWindowTouchMoveCancelled = false;
  /*
  Uses a "pointer" abstraction, which monitors UI events for both mouse and touch.
  Tracks when the pointer "drags" on a certain element, meaning down+move+up.

  Also, tracks if there was touch-scrolling.
  Also, can prevent touch-scrolling from happening.
  Also, can fire pointermove events when scrolling happens underneath, even when no real pointer movement.

  emits:
  - pointerdown
  - pointermove
  - pointerup
  */
  class PointerDragging {
      constructor(containerEl) {
          this.subjectEl = null;
          // options that can be directly assigned by caller
          this.selector = ''; // will cause subjectEl in all emitted events to be this element
          this.handleSelector = '';
          this.shouldIgnoreMove = false;
          this.shouldWatchScroll = true; // for simulating pointermove on scroll
          // internal states
          this.isDragging = false;
          this.isTouchDragging = false;
          this.wasTouchScroll = false; // HACK public
          // Mouse
          // ----------------------------------------------------------------------------------------------------
          this.handleMouseDown = (ev) => {
              if (!this.shouldIgnoreMouse() &&
                  isPrimaryMouseButton(ev) &&
                  this.tryStart(ev)) {
                  let pev = this.createEventFromMouse(ev, true);
                  this.emitter.trigger('pointerdown', pev);
                  this.initScrollWatch(pev);
                  if (!this.shouldIgnoreMove) {
                      document.addEventListener('mousemove', this.handleMouseMove);
                  }
                  document.addEventListener('mouseup', this.handleMouseUp);
              }
          };
          this.handleMouseMove = (ev) => {
              let pev = this.createEventFromMouse(ev);
              this.recordCoords(pev);
              this.emitter.trigger('pointermove', pev);
          };
          this.handleMouseUp = (ev) => {
              document.removeEventListener('mousemove', this.handleMouseMove);
              document.removeEventListener('mouseup', this.handleMouseUp);
              this.emitter.trigger('pointerup', this.createEventFromMouse(ev));
              this.cleanup(); // call last so that pointerup has access to props
          };
          // Touch
          // ----------------------------------------------------------------------------------------------------
          this.handleTouchStart = (ev) => {
              if (this.tryStart(ev)) {
                  this.isTouchDragging = true;
                  let pev = this.createEventFromTouch(ev, true);
                  this.emitter.trigger('pointerdown', pev);
                  this.initScrollWatch(pev);
                  // unlike mouse, need to attach to target, not document
                  // https://stackoverflow.com/a/45760014
                  let targetEl = ev.target;
                  if (!this.shouldIgnoreMove) {
                      targetEl.addEventListener('touchmove', this.handleTouchMove);
                  }
                  targetEl.addEventListener('touchend', this.handleTouchEnd);
                  targetEl.addEventListener('touchcancel', this.handleTouchEnd); // treat it as a touch end
                  // attach a handler to get called when ANY scroll action happens on the page.
                  // this was impossible to do with normal on/off because 'scroll' doesn't bubble.
                  // http://stackoverflow.com/a/32954565/96342
                  window.addEventListener('scroll', this.handleTouchScroll, true);
              }
          };
          this.handleTouchMove = (ev) => {
              if (this.isDragging) {
                  let pev = this.createEventFromTouch(ev);
                  this.recordCoords(pev);
                  this.emitter.trigger('pointermove', pev);
              }
          };
          this.handleTouchEnd = (ev) => {
              if (this.isDragging) { // done to guard against touchend followed by touchcancel
                  let targetEl = ev.target;
                  targetEl.removeEventListener('touchmove', this.handleTouchMove);
                  targetEl.removeEventListener('touchend', this.handleTouchEnd);
                  targetEl.removeEventListener('touchcancel', this.handleTouchEnd);
                  window.removeEventListener('scroll', this.handleTouchScroll, true); // useCaptured=true
                  this.emitter.trigger('pointerup', this.createEventFromTouch(ev));
                  this.cleanup(); // call last so that pointerup has access to props
                  this.isTouchDragging = false;
                  startIgnoringMouse();
              }
          };
          this.handleTouchScroll = () => {
              this.wasTouchScroll = true;
          };
          this.handleScroll = (ev) => {
              if (!this.shouldIgnoreMove) {
                  let pageX = (window.scrollX - this.prevScrollX) + this.prevPageX;
                  let pageY = (window.scrollY - this.prevScrollY) + this.prevPageY;
                  this.emitter.trigger('pointermove', {
                      origEvent: ev,
                      isTouch: this.isTouchDragging,
                      subjectEl: this.subjectEl,
                      pageX,
                      pageY,
                      deltaX: pageX - this.origPageX,
                      deltaY: pageY - this.origPageY,
                  });
              }
          };
          this.containerEl = containerEl;
          this.emitter = new Emitter();
          containerEl.addEventListener('mousedown', this.handleMouseDown);
          containerEl.addEventListener('touchstart', this.handleTouchStart, { passive: true });
          listenerCreated();
      }
      destroy() {
          this.containerEl.removeEventListener('mousedown', this.handleMouseDown);
          this.containerEl.removeEventListener('touchstart', this.handleTouchStart, { passive: true });
          listenerDestroyed();
      }
      cancel() {
          if (this.isDragging) {
              this.cleanup();
          }
      }
      tryStart(ev) {
          let subjectEl = this.querySubjectEl(ev);
          let downEl = ev.target;
          if (subjectEl &&
              (!this.handleSelector || downEl.closest(this.handleSelector))) {
              this.subjectEl = subjectEl;
              this.isDragging = true; // do this first so cancelTouchScroll will work
              this.wasTouchScroll = false;
              return true;
          }
          return false;
      }
      cleanup() {
          isWindowTouchMoveCancelled = false;
          this.isDragging = false;
          this.subjectEl = null;
          // keep wasTouchScroll around for later access
          this.destroyScrollWatch();
      }
      querySubjectEl(ev) {
          if (this.selector) {
              return ev.target.closest(this.selector);
          }
          return this.containerEl;
      }
      shouldIgnoreMouse() {
          return ignoreMouseDepth || this.isTouchDragging;
      }
      // can be called by user of this class, to cancel touch-based scrolling for the current drag
      cancelTouchScroll() {
          if (this.isDragging) {
              isWindowTouchMoveCancelled = true;
          }
      }
      // Scrolling that simulates pointermoves
      // ----------------------------------------------------------------------------------------------------
      initScrollWatch(ev) {
          if (this.shouldWatchScroll) {
              this.recordCoords(ev);
              window.addEventListener('scroll', this.handleScroll, true); // useCapture=true
          }
      }
      recordCoords(ev) {
          if (this.shouldWatchScroll) {
              this.prevPageX = ev.pageX;
              this.prevPageY = ev.pageY;
              this.prevScrollX = window.scrollX;
              this.prevScrollY = window.scrollY;
          }
      }
      destroyScrollWatch() {
          if (this.shouldWatchScroll) {
              window.removeEventListener('scroll', this.handleScroll, true); // useCaptured=true
          }
      }
      // Event Normalization
      // ----------------------------------------------------------------------------------------------------
      createEventFromMouse(ev, isFirst) {
          let deltaX = 0;
          let deltaY = 0;
          // TODO: repeat code
          if (isFirst) {
              this.origPageX = ev.pageX;
              this.origPageY = ev.pageY;
          }
          else {
              deltaX = ev.pageX - this.origPageX;
              deltaY = ev.pageY - this.origPageY;
          }
          return {
              origEvent: ev,
              isTouch: false,
              subjectEl: this.subjectEl,
              pageX: ev.pageX,
              pageY: ev.pageY,
              deltaX,
              deltaY,
          };
      }
      createEventFromTouch(ev, isFirst) {
          let touches = ev.touches;
          let pageX;
          let pageY;
          let deltaX = 0;
          let deltaY = 0;
          // if touch coords available, prefer,
          // because FF would give bad ev.pageX ev.pageY
          if (touches && touches.length) {
              pageX = touches[0].pageX;
              pageY = touches[0].pageY;
          }
          else {
              pageX = ev.pageX;
              pageY = ev.pageY;
          }
          // TODO: repeat code
          if (isFirst) {
              this.origPageX = pageX;
              this.origPageY = pageY;
          }
          else {
              deltaX = pageX - this.origPageX;
              deltaY = pageY - this.origPageY;
          }
          return {
              origEvent: ev,
              isTouch: true,
              subjectEl: this.subjectEl,
              pageX,
              pageY,
              deltaX,
              deltaY,
          };
      }
  }
  // Returns a boolean whether this was a left mouse click and no ctrl key (which means right click on Mac)
  function isPrimaryMouseButton(ev) {
      return ev.button === 0 && !ev.ctrlKey;
  }
  // Ignoring fake mouse events generated by touch
  // ----------------------------------------------------------------------------------------------------
  function startIgnoringMouse() {
      ignoreMouseDepth += 1;
      setTimeout(() => {
          ignoreMouseDepth -= 1;
      }, config.touchMouseIgnoreWait);
  }
  // We want to attach touchmove as early as possible for Safari
  // ----------------------------------------------------------------------------------------------------
  function listenerCreated() {
      listenerCnt += 1;
      if (listenerCnt === 1) {
          window.addEventListener('touchmove', onWindowTouchMove, { passive: false });
      }
  }
  function listenerDestroyed() {
      listenerCnt -= 1;
      if (!listenerCnt) {
          window.removeEventListener('touchmove', onWindowTouchMove, { passive: false });
      }
  }
  function onWindowTouchMove(ev) {
      if (isWindowTouchMoveCancelled) {
          ev.preventDefault();
      }
  }

  /*
  An effect in which an element follows the movement of a pointer across the screen.
  The moving element is a clone of some other element.
  Must call start + handleMove + stop.
  */
  class ElementMirror {
      constructor() {
          this.isVisible = false; // must be explicitly enabled
          this.sourceEl = null;
          this.mirrorEl = null;
          this.sourceElRect = null; // screen coords relative to viewport
          // options that can be set directly by caller
          this.parentNode = document.body; // HIGHLY SUGGESTED to set this to sidestep ShadowDOM issues
          this.zIndex = 9999;
          this.revertDuration = 0;
          this.colorScheme = '';
      }
      start(sourceEl, pageX, pageY) {
          this.sourceEl = sourceEl;
          this.sourceElRect = this.sourceEl.getBoundingClientRect();
          this.origScreenX = pageX - window.scrollX;
          this.origScreenY = pageY - window.scrollY;
          this.deltaX = 0;
          this.deltaY = 0;
          this.updateElPosition();
      }
      handleMove(pageX, pageY) {
          this.deltaX = (pageX - window.scrollX) - this.origScreenX;
          this.deltaY = (pageY - window.scrollY) - this.origScreenY;
          this.updateElPosition();
      }
      // can be called before start
      setIsVisible(bool) {
          if (bool) {
              if (!this.isVisible) {
                  if (this.mirrorEl) {
                      // important because competes with util.module.css classNames, which are all important
                      // TODO: attach a util className here instead?
                      this.mirrorEl.style.setProperty('display', '', 'important');
                  }
                  this.isVisible = bool; // needs to happen before updateElPosition
                  this.updateElPosition(); // because was not updating the position while invisible
              }
          }
          else if (this.isVisible) {
              if (this.mirrorEl) {
                  // important because competes with util.module.css classNames, which are all important
                  // TODO: attach a util className here instead?
                  this.mirrorEl.style.setProperty('display', 'none', 'important');
              }
              this.isVisible = bool;
          }
      }
      // always async
      stop(needsRevertAnimation, callback) {
          let done = () => {
              this.cleanup();
              callback();
          };
          if (needsRevertAnimation &&
              this.mirrorEl &&
              this.isVisible &&
              this.revertDuration && // if 0, transition won't work
              (this.deltaX || this.deltaY) // if same coords, transition won't work
          ) {
              this.doRevertAnimation(done, this.revertDuration);
          }
          else {
              setTimeout(done, 0);
          }
      }
      doRevertAnimation(callback, revertDuration) {
          let mirrorEl = this.mirrorEl;
          let finalSourceElRect = this.sourceEl.getBoundingClientRect(); // because autoscrolling might have happened
          mirrorEl.style.transition =
              'top ' + revertDuration + 'ms,' +
                  'left ' + revertDuration + 'ms';
          applyStyle(mirrorEl, {
              left: finalSourceElRect.left,
              top: finalSourceElRect.top,
          });
          whenTransitionDone(mirrorEl, () => {
              mirrorEl.style.transition = '';
              callback();
          });
      }
      cleanup() {
          if (this.mirrorEl) {
              this.mirrorEl.remove();
              this.mirrorEl = null;
          }
          this.sourceEl = null;
      }
      updateElPosition() {
          if (this.sourceEl && this.isVisible) {
              applyStyle(this.getMirrorEl(), {
                  left: this.sourceElRect.left + this.deltaX,
                  top: this.sourceElRect.top + this.deltaY,
              });
          }
      }
      getMirrorEl() {
          let sourceElRect = this.sourceElRect;
          let mirrorEl = this.mirrorEl;
          if (!mirrorEl) {
              mirrorEl = this.mirrorEl = this.sourceEl.cloneNode(true); // cloneChildren=true
              // we don't want long taps or any mouse interaction causing selection/menus.
              // would use preventSelection(), but that prevents selectstart, causing problems.
              // TODO: make className for this?
              mirrorEl.style.userSelect = 'none';
              mirrorEl.style.webkitUserSelect = 'none';
              mirrorEl.style.pointerEvents = 'none';
              if (this.colorScheme) {
                  mirrorEl.setAttribute('data-color-scheme', this.colorScheme);
              }
              mirrorEl.classList.add(classNames.borderBoxRoot);
              applyStyle(mirrorEl, {
                  position: 'fixed',
                  zIndex: this.zIndex,
                  visibility: '', // in case original element was hidden by the drag effect
                  width: sourceElRect.right - sourceElRect.left, // explicit height in case there was a 'right' value
                  height: sourceElRect.bottom - sourceElRect.top, // explicit width in case there was a 'bottom' value
                  right: 'auto', // erase and set width instead
                  bottom: 'auto', // erase and set height instead
                  margin: 0,
              });
              this.parentNode.appendChild(mirrorEl);
          }
          return mirrorEl;
      }
  }

  /* eslint max-classes-per-file: "off" */
  /*
  An object for getting/setting scroll-related information for an element.
  Internally, this is done very differently for window versus DOM element,
  so this object serves as a common interface.
  */
  class ScrollController {
      getMaxScrollTop() {
          return this.getScrollHeight() - this.getClientHeight();
      }
      getMaxScrollLeft() {
          return this.getScrollWidth() - this.getClientWidth();
      }
      canScrollVertically() {
          return this.getMaxScrollTop() > 0;
      }
      canScrollHorizontally() {
          return this.getMaxScrollLeft() > 0;
      }
      canScrollUp() {
          return this.getScrollTop() > 0;
      }
      canScrollDown() {
          return this.getScrollTop() < this.getMaxScrollTop();
      }
      canScrollLeft() {
          return this.getScrollLeft() > 0;
      }
      canScrollRight() {
          return this.getScrollLeft() < this.getMaxScrollLeft();
      }
  }
  class ElementScrollController extends ScrollController {
      constructor(el) {
          super();
          this.el = el;
      }
      getScrollTop() {
          return this.el.scrollTop;
      }
      getScrollLeft() {
          return this.el.scrollLeft;
      }
      setScrollTop(top) {
          this.el.scrollTop = top;
      }
      setScrollLeft(left) {
          this.el.scrollLeft = left;
      }
      getScrollWidth() {
          return this.el.scrollWidth;
      }
      getScrollHeight() {
          return this.el.scrollHeight;
      }
      getClientHeight() {
          return this.el.clientHeight;
      }
      getClientWidth() {
          return this.el.clientWidth;
      }
  }
  class WindowScrollController extends ScrollController {
      getScrollTop() {
          return window.scrollY;
      }
      getScrollLeft() {
          return window.scrollX;
      }
      setScrollTop(n) {
          window.scroll(window.scrollX, n);
      }
      setScrollLeft(n) {
          window.scroll(n, window.scrollY);
      }
      getScrollWidth() {
          return document.documentElement.scrollWidth;
      }
      getScrollHeight() {
          return document.documentElement.scrollHeight;
      }
      getClientHeight() {
          return document.documentElement.clientHeight;
      }
      getClientWidth() {
          return document.documentElement.clientWidth;
      }
  }

  /*
  Is a cache for a given element's scroll information (all the info that ScrollController stores)
  in addition the "client rectangle" of the element.. the area within the scrollbars.

  The cache can be in one of two modes:
  - doesListening:false - ignores when the container is scrolled by someone else
  - doesListening:true - watch for scrolling and update the cache
  */
  class ScrollGeomCache extends ScrollController {
      constructor(scrollController, doesListening) {
          super();
          this.handleScroll = () => {
              this.scrollTop = this.scrollController.getScrollTop();
              this.scrollLeft = this.scrollController.getScrollLeft();
              this.handleScrollChange();
          };
          this.scrollController = scrollController;
          this.doesListening = doesListening;
          this.scrollTop = this.origScrollTop = scrollController.getScrollTop();
          this.scrollLeft = this.origScrollLeft = scrollController.getScrollLeft();
          this.scrollWidth = scrollController.getScrollWidth();
          this.scrollHeight = scrollController.getScrollHeight();
          this.clientWidth = scrollController.getClientWidth();
          this.clientHeight = scrollController.getClientHeight();
          this.clientRect = this.computeClientRect(); // do last in case it needs cached values
          if (this.doesListening) {
              this.getEventTarget().addEventListener('scroll', this.handleScroll);
          }
      }
      destroy() {
          if (this.doesListening) {
              this.getEventTarget().removeEventListener('scroll', this.handleScroll);
          }
      }
      getScrollTop() {
          return this.scrollTop;
      }
      getScrollLeft() {
          return this.scrollLeft;
      }
      setScrollTop(top) {
          this.scrollController.setScrollTop(top);
          if (!this.doesListening) {
              // we are not relying on the element to normalize out-of-bounds scroll values
              // so we need to sanitize ourselves
              this.scrollTop = Math.max(Math.min(top, this.getMaxScrollTop()), 0);
              this.handleScrollChange();
          }
      }
      setScrollLeft(top) {
          this.scrollController.setScrollLeft(top);
          if (!this.doesListening) {
              // we are not relying on the element to normalize out-of-bounds scroll values
              // so we need to sanitize ourselves
              this.scrollLeft = Math.max(Math.min(top, this.getMaxScrollLeft()), 0);
              this.handleScrollChange();
          }
      }
      getClientWidth() {
          return this.clientWidth;
      }
      getClientHeight() {
          return this.clientHeight;
      }
      getScrollWidth() {
          return this.scrollWidth;
      }
      getScrollHeight() {
          return this.scrollHeight;
      }
      handleScrollChange() {
      }
  }

  class ElementScrollGeomCache extends ScrollGeomCache {
      constructor(el, doesListening) {
          super(new ElementScrollController(el), doesListening);
      }
      getEventTarget() {
          return this.scrollController.el;
      }
      computeClientRect() {
          return computeInnerRect(this.scrollController.el);
      }
  }

  class WindowScrollGeomCache extends ScrollGeomCache {
      constructor(doesListening) {
          super(new WindowScrollController(), doesListening);
      }
      getEventTarget() {
          return window;
      }
      computeClientRect() {
          return {
              left: this.scrollLeft,
              right: this.scrollLeft + this.clientWidth,
              top: this.scrollTop,
              bottom: this.scrollTop + this.clientHeight,
          };
      }
      // the window is the only scroll object that changes it's rectangle relative
      // to the document's topleft as it scrolls
      handleScrollChange() {
          this.clientRect = this.computeClientRect();
      }
  }

  // If available we are using native "performance" API instead of "Date"
  // Read more about it on MDN:
  // https://developer.mozilla.org/en-US/docs/Web/API/Performance
  const getTime = typeof performance === 'function' ? performance.now : Date.now;
  /*
  For a pointer interaction, automatically scrolls certain scroll containers when the pointer
  approaches the edge.

  The caller must call start + handleMove + stop.
  */
  class AutoScroller {
      constructor() {
          // options that can be set by caller
          this.isEnabled = true;
          this.scrollQuery = [window, `.${classNames.internalScroller}`];
          this.edgeThreshold = 50; // pixels
          this.maxVelocity = 300; // pixels per second
          // internal state
          this.pointerScreenX = null;
          this.pointerScreenY = null;
          this.isAnimating = false;
          this.scrollCaches = null;
          // protect against the initial pointerdown being too close to an edge and starting the scroll
          this.everMovedUp = false;
          this.everMovedDown = false;
          this.everMovedLeft = false;
          this.everMovedRight = false;
          this.animate = () => {
              if (this.isAnimating) { // wasn't cancelled between animation calls
                  let edge = this.computeBestEdge(this.pointerScreenX + window.scrollX, this.pointerScreenY + window.scrollY);
                  if (edge) {
                      let now = getTime();
                      this.handleSide(edge, (now - this.msSinceRequest) / 1000);
                      this.requestAnimation(now);
                  }
                  else {
                      this.isAnimating = false; // will stop animation
                  }
              }
          };
      }
      start(pageX, pageY, scrollStartEl) {
          if (this.isEnabled) {
              this.scrollCaches = this.buildCaches(scrollStartEl);
              this.pointerScreenX = null;
              this.pointerScreenY = null;
              this.everMovedUp = false;
              this.everMovedDown = false;
              this.everMovedLeft = false;
              this.everMovedRight = false;
              this.handleMove(pageX, pageY);
          }
      }
      handleMove(pageX, pageY) {
          if (this.isEnabled) {
              let pointerScreenX = pageX - window.scrollX;
              let pointerScreenY = pageY - window.scrollY;
              let yDelta = this.pointerScreenY === null ? 0 : pointerScreenY - this.pointerScreenY;
              let xDelta = this.pointerScreenX === null ? 0 : pointerScreenX - this.pointerScreenX;
              if (yDelta < 0) {
                  this.everMovedUp = true;
              }
              else if (yDelta > 0) {
                  this.everMovedDown = true;
              }
              if (xDelta < 0) {
                  this.everMovedLeft = true;
              }
              else if (xDelta > 0) {
                  this.everMovedRight = true;
              }
              this.pointerScreenX = pointerScreenX;
              this.pointerScreenY = pointerScreenY;
              if (!this.isAnimating) {
                  this.isAnimating = true;
                  this.requestAnimation(getTime());
              }
          }
      }
      stop() {
          if (this.isEnabled) {
              this.isAnimating = false; // will stop animation
              for (let scrollCache of this.scrollCaches) {
                  scrollCache.destroy();
              }
              this.scrollCaches = null;
          }
      }
      requestAnimation(now) {
          this.msSinceRequest = now;
          requestAnimationFrame(this.animate);
      }
      handleSide(edge, seconds) {
          let { scrollCache } = edge;
          let { edgeThreshold } = this;
          let invDistance = edgeThreshold - edge.distance;
          let velocity = // the closer to the edge, the faster we scroll
           ((invDistance * invDistance) / (edgeThreshold * edgeThreshold)) * // quadratic
              this.maxVelocity * seconds;
          let sign = 1;
          switch (edge.name) {
              case 'left':
                  sign = -1;
              // falls through
              case 'right':
                  scrollCache.setScrollLeft(scrollCache.getScrollLeft() + velocity * sign);
                  break;
              case 'top':
                  sign = -1;
              // falls through
              case 'bottom':
                  scrollCache.setScrollTop(scrollCache.getScrollTop() + velocity * sign);
                  break;
          }
      }
      // left/top are relative to document topleft
      computeBestEdge(left, top) {
          let { edgeThreshold } = this;
          let bestSide = null;
          let scrollCaches = this.scrollCaches || [];
          for (let scrollCache of scrollCaches) {
              let rect = scrollCache.clientRect;
              let leftDist = left - rect.left;
              let rightDist = rect.right - left;
              let topDist = top - rect.top;
              let bottomDist = rect.bottom - top;
              // completely within the rect?
              if (leftDist >= 0 && rightDist >= 0 && topDist >= 0 && bottomDist >= 0) {
                  if (topDist <= edgeThreshold && this.everMovedUp && scrollCache.canScrollUp() &&
                      (!bestSide || bestSide.distance > topDist)) {
                      bestSide = { scrollCache, name: 'top', distance: topDist };
                  }
                  if (bottomDist <= edgeThreshold && this.everMovedDown && scrollCache.canScrollDown() &&
                      (!bestSide || bestSide.distance > bottomDist)) {
                      bestSide = { scrollCache, name: 'bottom', distance: bottomDist };
                  }
                  /*
                  TODO: fix broken RTL scrolling. canScrollLeft always returning false
                  https://github.com/fullcalendar/fullcalendar/issues/4837
                  */
                  if (leftDist <= edgeThreshold && this.everMovedLeft && scrollCache.canScrollLeft() &&
                      (!bestSide || bestSide.distance > leftDist)) {
                      bestSide = { scrollCache, name: 'left', distance: leftDist };
                  }
                  if (rightDist <= edgeThreshold && this.everMovedRight && scrollCache.canScrollRight() &&
                      (!bestSide || bestSide.distance > rightDist)) {
                      bestSide = { scrollCache, name: 'right', distance: rightDist };
                  }
              }
          }
          return bestSide;
      }
      buildCaches(scrollStartEl) {
          return this.queryScrollEls(scrollStartEl).map((el) => {
              if (el === window) {
                  return new WindowScrollGeomCache(false); // false = don't listen to user-generated scrolls
              }
              return new ElementScrollGeomCache(el, false); // false = don't listen to user-generated scrolls
          });
      }
      queryScrollEls(scrollStartEl) {
          let els = [];
          for (let query of this.scrollQuery) {
              if (typeof query === 'object') {
                  els.push(query);
              }
              else {
                  /*
                  TODO: in the future, always have auto-scroll happen on element where current Hit came from
                  Ticket: https://github.com/fullcalendar/fullcalendar/issues/4593
                  */
                  els.push(...Array.prototype.slice.call(scrollStartEl.getRootNode().querySelectorAll(query)));
              }
          }
          return els;
      }
  }

  /*
  Monitors dragging on an element. Has a number of high-level features:
  - minimum distance required before dragging
  - minimum wait time ("delay") before dragging
  - a mirror element that follows the pointer
  */
  class FeaturefulElementDragging extends ElementDragging {
      constructor(containerEl, selector) {
          super(containerEl);
          this.containerEl = containerEl;
          // options that can be directly set by caller
          // the caller can also set the PointerDragging's options as well
          this.delay = null;
          this.minDistance = 0;
          this.touchScrollAllowed = true; // prevents drag from starting and blocks scrolling during drag
          this.mirrorNeedsRevert = false;
          this.isInteracting = false; // is the user validly moving the pointer? lasts until pointerup
          this.isDragging = false; // is it INTENTFULLY dragging? lasts until after revert animation
          this.isDelayEnded = false;
          this.isDistanceSurpassed = false;
          this.delayTimeoutId = null;
          this.onPointerDown = (ev) => {
              if (!this.isDragging) { // so new drag doesn't happen while revert animation is going
                  this.isInteracting = true;
                  this.isDelayEnded = false;
                  this.isDistanceSurpassed = false;
                  this.emitter.trigger('pointerdown', ev);
                  if (this.isInteracting) { // not cancelled?
                      preventSelection(document.body);
                      preventContextMenu(document.body);
                      // prevent links from being visited if there's an eventual drag.
                      // also prevents selection in older browsers (maybe?).
                      // not necessary for touch, besides, browser would complain about passiveness.
                      if (!ev.isTouch) {
                          ev.origEvent.preventDefault();
                      }
                      // actions related to initiating dragstart+dragmove+dragend...
                      this.mirror.setIsVisible(false); // reset. caller must set-visible
                      this.mirror.start(ev.subjectEl, ev.pageX, ev.pageY); // must happen on first pointer down
                      this.startDelay(ev);
                      if (!this.minDistance) {
                          this.handleDistanceSurpassed(ev);
                      }
                  }
              }
          };
          this.onPointerMove = (ev) => {
              if (this.isInteracting) {
                  this.emitter.trigger('pointermove', ev);
                  if (!this.isDistanceSurpassed) {
                      let minDistance = this.minDistance;
                      let distanceSq; // current distance from the origin, squared
                      let { deltaX, deltaY } = ev;
                      distanceSq = deltaX * deltaX + deltaY * deltaY;
                      if (distanceSq >= minDistance * minDistance) { // use pythagorean theorem
                          this.handleDistanceSurpassed(ev);
                      }
                  }
                  if (this.isDragging) {
                      // a real pointer move? (not one simulated by scrolling)
                      if (ev.origEvent.type !== 'scroll') {
                          this.mirror.handleMove(ev.pageX, ev.pageY);
                          this.autoScroller.handleMove(ev.pageX, ev.pageY);
                      }
                      this.emitter.trigger('dragmove', ev);
                  }
              }
          };
          this.onPointerUp = (ev) => {
              if (this.isInteracting) {
                  this.isInteracting = false;
                  allowSelection(document.body);
                  allowContextMenu(document.body);
                  this.emitter.trigger('pointerup', ev); // can potentially set mirrorNeedsRevert
                  if (this.isDragging) {
                      this.autoScroller.stop();
                      this.tryStopDrag(ev); // which will stop the mirror
                  }
                  if (this.delayTimeoutId) {
                      clearTimeout(this.delayTimeoutId);
                      this.delayTimeoutId = null;
                  }
              }
          };
          let pointer = this.pointer = new PointerDragging(containerEl);
          pointer.emitter.on('pointerdown', this.onPointerDown);
          pointer.emitter.on('pointermove', this.onPointerMove);
          pointer.emitter.on('pointerup', this.onPointerUp);
          if (selector) {
              pointer.selector = selector;
          }
          this.mirror = new ElementMirror();
          this.autoScroller = new AutoScroller();
      }
      destroy() {
          this.pointer.destroy();
          // HACK: simulate a pointer-up to end the current drag
          // TODO: fire 'dragend' directly and stop interaction. discourage use of pointerup event (b/c might not fire)
          this.onPointerUp({});
      }
      startDelay(ev) {
          if (typeof this.delay === 'number') {
              this.delayTimeoutId = setTimeout(() => {
                  this.delayTimeoutId = null;
                  this.handleDelayEnd(ev);
              }, this.delay); // not assignable to number!
          }
          else {
              this.handleDelayEnd(ev);
          }
      }
      handleDelayEnd(ev) {
          this.isDelayEnded = true;
          this.tryStartDrag(ev);
      }
      handleDistanceSurpassed(ev) {
          this.isDistanceSurpassed = true;
          this.tryStartDrag(ev);
      }
      tryStartDrag(ev) {
          if (this.isDelayEnded && this.isDistanceSurpassed) {
              if (!this.pointer.wasTouchScroll || this.touchScrollAllowed) {
                  this.isDragging = true;
                  this.mirrorNeedsRevert = false;
                  this.autoScroller.start(ev.pageX, ev.pageY, this.containerEl);
                  this.emitter.trigger('dragstart', ev);
                  if (this.touchScrollAllowed === false) {
                      this.pointer.cancelTouchScroll();
                  }
              }
          }
      }
      tryStopDrag(ev) {
          // .stop() is ALWAYS asynchronous, which we NEED because we want all pointerup events
          // that come from the document to fire beforehand. much more convenient this way.
          this.mirror.stop(this.mirrorNeedsRevert, this.stopDrag.bind(this, ev));
      }
      stopDrag(ev) {
          this.isDragging = false;
          this.emitter.trigger('dragend', ev);
      }
      // fill in the implementations...
      /*
      Can only be called by pointerdown to prevent drag
      */
      cancel() {
          if (this.isInteracting) {
              this.isInteracting = false;
              this.pointer.cancel();
          }
      }
      setMirrorIsVisible(bool) {
          this.mirror.setIsVisible(bool);
      }
      setMirrorNeedsRevert(bool) {
          this.mirrorNeedsRevert = bool;
      }
      setAutoScrollEnabled(bool) {
          this.autoScroller.isEnabled = bool;
      }
  }

  /*
  When this class is instantiated, it records the offset of an element (relative to the document topleft),
  and continues to monitor scrolling, updating the cached coordinates if it needs to.
  Does not access the DOM after instantiation, so highly performant.

  Also keeps track of all scrolling/overflow:hidden containers that are parents of the given element
  and an determine if a given point is inside the combined clipping rectangle.
  */
  class OffsetTracker {
      constructor(el) {
          this.el = el;
          this.origRect = computeRect(el);
          this.isRtl = computeElIsRtl(el);
          // will work fine for divs that have overflow:hidden
          this.scrollCaches = getClippingParents(el).map((scrollEl) => new ElementScrollGeomCache(scrollEl, true));
      }
      destroy() {
          for (let scrollCache of this.scrollCaches) {
              scrollCache.destroy();
          }
      }
      computeLeft() {
          let left = this.origRect.left;
          for (let scrollCache of this.scrollCaches) {
              left += scrollCache.origScrollLeft - scrollCache.getScrollLeft();
          }
          return left;
      }
      computeTop() {
          let top = this.origRect.top;
          for (let scrollCache of this.scrollCaches) {
              top += scrollCache.origScrollTop - scrollCache.getScrollTop();
          }
          return top;
      }
      isWithinClipping(pageX, pageY) {
          let point = { left: pageX, top: pageY };
          for (let scrollCache of this.scrollCaches) {
              if (!isIgnoredClipping(scrollCache.getEventTarget()) &&
                  !pointInsideRect(point, scrollCache.clientRect)) {
                  return false;
              }
          }
          return true;
      }
  }
  // certain clipping containers should never constrain interactions, like <html> and <body>
  // https://github.com/fullcalendar/fullcalendar/issues/3615
  function isIgnoredClipping(node) {
      let tagName = node.tagName;
      return tagName === 'HTML' || tagName === 'BODY';
  }

  /*
  Tracks movement over multiple droppable areas (aka "hits")
  that exist in one or more DateComponents.
  Relies on an existing draggable.

  emits:
  - pointerdown
  - dragstart
  - hitchange - fires initially, even if not over a hit
  - pointerup
  - (hitchange - again, to null, if ended over a hit)
  - dragend
  */
  class HitDragging {
      constructor(dragging, droppableStore) {
          // options that can be set by caller
          this.useSubjectCenter = false;
          this.requireInitial = true; // if doesn't start out on a hit, won't emit any events
          this.disablePointCheck = false;
          this.initialHit = null;
          this.movingHit = null;
          this.finalHit = null; // won't ever be populated if shouldIgnoreMove
          this.handlePointerDown = (ev) => {
              let { dragging } = this;
              this.initialHit = null;
              this.movingHit = null;
              this.finalHit = null;
              this.prepareHits();
              this.processFirstCoord(ev);
              if (this.initialHit || !this.requireInitial) {
                  // TODO: fire this before computing processFirstCoord, so listeners can cancel. this gets fired by almost every handler :(
                  this.emitter.trigger('pointerdown', ev);
              }
              else {
                  dragging.cancel();
              }
          };
          this.handleDragStart = (ev) => {
              this.emitter.trigger('dragstart', ev);
              this.handleMove(ev, true); // force = fire even if initially null
          };
          this.handleDragMove = (ev) => {
              this.emitter.trigger('dragmove', ev);
              this.handleMove(ev);
          };
          this.handlePointerUp = (ev) => {
              this.releaseHits();
              this.emitter.trigger('pointerup', ev);
          };
          this.handleDragEnd = (ev) => {
              if (this.movingHit) {
                  this.emitter.trigger('hitupdate', null, true, ev);
              }
              this.finalHit = this.movingHit;
              this.movingHit = null;
              this.emitter.trigger('dragend', ev);
          };
          this.droppableStore = droppableStore;
          dragging.emitter.on('pointerdown', this.handlePointerDown);
          dragging.emitter.on('dragstart', this.handleDragStart);
          dragging.emitter.on('dragmove', this.handleDragMove);
          dragging.emitter.on('pointerup', this.handlePointerUp);
          dragging.emitter.on('dragend', this.handleDragEnd);
          this.dragging = dragging;
          this.emitter = new Emitter();
      }
      // sets initialHit
      // sets coordAdjust
      processFirstCoord(ev) {
          let origPoint = { left: ev.pageX, top: ev.pageY };
          let adjustedPoint = origPoint;
          let subjectEl = ev.subjectEl;
          let subjectRect;
          if (subjectEl instanceof HTMLElement) { // i.e. not a Document/ShadowRoot
              subjectRect = computeRect(subjectEl);
              adjustedPoint = constrainPoint(adjustedPoint, subjectRect);
          }
          let initialHit = this.initialHit = this.queryHitForOffset(adjustedPoint.left, adjustedPoint.top);
          if (initialHit) {
              if (this.useSubjectCenter && subjectRect) {
                  let slicedSubjectRect = intersectRects(subjectRect, initialHit.rect);
                  if (slicedSubjectRect) {
                      adjustedPoint = getRectCenter(slicedSubjectRect);
                  }
              }
              this.coordAdjust = diffPoints(adjustedPoint, origPoint);
          }
          else {
              this.coordAdjust = { left: 0, top: 0 };
          }
      }
      handleMove(ev, forceHandle) {
          let hit = this.queryHitForOffset(ev.pageX + this.coordAdjust.left, ev.pageY + this.coordAdjust.top);
          if (forceHandle || !isHitsEqual(this.movingHit, hit)) {
              this.movingHit = hit;
              this.emitter.trigger('hitupdate', hit, false, ev);
          }
      }
      prepareHits() {
          this.offsetTrackers = mapHash(this.droppableStore, (interactionSettings) => {
              interactionSettings.component.prepareHits();
              return new OffsetTracker(interactionSettings.el);
          });
      }
      releaseHits() {
          let { offsetTrackers } = this;
          for (let id in offsetTrackers) {
              offsetTrackers[id].destroy();
          }
          this.offsetTrackers = {};
      }
      queryHitForOffset(offsetLeft, offsetTop) {
          let { droppableStore, offsetTrackers } = this;
          let bestHit = null;
          for (let id in droppableStore) {
              let component = droppableStore[id].component;
              let offsetTracker = offsetTrackers[id];
              if (offsetTracker && // wasn't destroyed mid-drag
                  offsetTracker.isWithinClipping(offsetLeft, offsetTop)) {
                  let originLeft = offsetTracker.computeLeft();
                  let originTop = offsetTracker.computeTop();
                  let positionLeft = offsetLeft - originLeft;
                  let positionTop = offsetTop - originTop;
                  let { origRect } = offsetTracker;
                  let width = origRect.right - origRect.left;
                  let height = origRect.bottom - origRect.top;
                  if (
                  // must be within the element's bounds
                  positionLeft >= 0 && positionLeft < width &&
                      positionTop >= 0 && positionTop < height) {
                      let hit = component.queryHit(offsetTracker.isRtl, positionLeft, positionTop, width, height);
                      if (hit && (
                      // make sure the hit is within activeRange, meaning it's not a dead cell
                      rangeContainsRange(hit.dateProfile.activeRange, hit.dateSpan.range)) &&
                          // Ensure the component we are querying for the hit is accessibly my the pointer
                          // Prevents obscured calendars (ex: under a modal dialog) from accepting hit
                          // https://github.com/fullcalendar/fullcalendar/issues/5026
                          (this.disablePointCheck ||
                              offsetTracker.el.contains(offsetTracker.el.getRootNode().elementFromPoint(
                              // add-back origins to get coordinate relative to top-left of window viewport
                              positionLeft + originLeft - window.scrollX, positionTop + originTop - window.scrollY))) &&
                          (!bestHit || hit.layer > bestHit.layer)) {
                          hit.componentId = id;
                          hit.context = component.context;
                          // TODO: better way to re-orient rectangle
                          hit.rect.left += originLeft;
                          hit.rect.right += originLeft;
                          hit.rect.top += originTop;
                          hit.rect.bottom += originTop;
                          bestHit = hit;
                      }
                  }
              }
          }
          return bestHit;
      }
  }
  function isHitsEqual(hit0, hit1) {
      if (!hit0 && !hit1) {
          return true;
      }
      if (Boolean(hit0) !== Boolean(hit1)) {
          return false;
      }
      return isDateSpansEqual(hit0.dateSpan, hit1.dateSpan);
  }

  function buildDatePointApiWithContext(dateSpan, context) {
      let props = {};
      for (let transform of context.pluginHooks.datePointTransforms) {
          Object.assign(props, transform(dateSpan, context));
      }
      Object.assign(props, buildDatePointApi(dateSpan, context.dateEnv));
      return props;
  }
  function buildDatePointApi(span, dateEnv) {
      const start = buildRangeEdgeOutput(span.range.start, span.instantStartMs, dateEnv, span.allDay);
      return {
          date: start.date,
          dateStr: start.dateStr,
          allDay: span.allDay,
      };
  }

  /*
  Monitors when the user clicks on a specific date/time of a component.
  A pointerdown+pointerup on the same "hit" constitutes a click.
  */
  class DateClicking extends Interaction {
      constructor(settings) {
          super(settings);
          this.handlePointerDown = (pev) => {
              let { dragging } = this;
              let downEl = pev.origEvent.target;
              /*
              If no dateClick, allow text on dates to be text-selectable
              */
              const canDateClick = this.component.context.emitter.hasHandlers('dateClick') &&
                  this.component.isValidDateDownEl(downEl);
              if (!canDateClick) {
                  dragging.cancel();
              }
          };
          // won't even fire if moving was ignored
          this.handleDragEnd = (ev) => {
              let { component } = this;
              let { pointer } = this.dragging;
              if (!pointer.wasTouchScroll) {
                  let { initialHit, finalHit } = this.hitDragging;
                  if (initialHit && finalHit && isHitsEqual(initialHit, finalHit)) {
                      let { context } = component;
                      let data = {
                          ...buildDatePointApiWithContext(initialHit.dateSpan, context),
                          dayEl: initialHit.getDayEl(),
                          jsEvent: ev.origEvent,
                          view: context.viewApi || context.calendarApi.view,
                      };
                      context.emitter.trigger('dateClick', data);
                  }
              }
          };
          // we DO want to watch pointer moves because otherwise finalHit won't get populated
          this.dragging = new FeaturefulElementDragging(settings.el);
          this.dragging.autoScroller.isEnabled = false;
          let hitDragging = this.hitDragging = new HitDragging(this.dragging, interactionSettingsToStore(settings));
          hitDragging.emitter.on('pointerdown', this.handlePointerDown);
          hitDragging.emitter.on('dragend', this.handleDragEnd);
      }
      destroy() {
          this.dragging.destroy();
      }
  }

  /*
  Tracks when the user selects a portion of time of a component,
  constituted by a drag over date cells, with a possible delay at the beginning of the drag.
  */
  class DateSelecting extends Interaction {
      constructor(settings) {
          super(settings);
          this.dragSelection = null;
          this.handlePointerDown = (ev) => {
              let { component, dragging } = this;
              let { options } = component.context;
              let canDateSelect = options.selectable &&
                  component.isValidDateDownEl(ev.origEvent.target);
              if (!canDateSelect) {
                  dragging.cancel();
              }
              else {
                  // if touch, require user to hold down
                  dragging.delay = ev.isTouch ? getComponentTouchDelay$1(component) : null;
              }
          };
          this.handleDragStart = (ev) => {
              this.component.context.calendarApi.unselect(ev); // unselect previous selections
          };
          this.handleHitUpdate = (hit, isFinal) => {
              let { context } = this.component;
              let dragSelection = null;
              let isInvalid = false;
              if (hit) {
                  let initialHit = this.hitDragging.initialHit;
                  let disallowed = hit.componentId === initialHit.componentId
                      && this.isHitComboAllowed
                      && !this.isHitComboAllowed(initialHit, hit);
                  if (!disallowed) {
                      dragSelection = joinHitsIntoSelection(initialHit, hit, context.pluginHooks.dateSelectionTransformers);
                  }
                  if (!dragSelection || !isDateSelectionValid(dragSelection, hit.dateProfile, context)) {
                      isInvalid = true;
                      dragSelection = null;
                  }
              }
              if (dragSelection) {
                  context.dispatch({ type: 'SELECT_DATES', selection: dragSelection });
              }
              else if (!isFinal) { // only unselect if moved away while dragging
                  context.dispatch({ type: 'UNSELECT_DATES' });
              }
              if (!isInvalid) {
                  enableCursor();
              }
              else {
                  disableCursor();
              }
              if (!isFinal) {
                  this.dragSelection = dragSelection; // only clear if moved away from all hits while dragging
              }
          };
          this.handlePointerUp = (pev) => {
              if (this.dragSelection) {
                  // selection is already rendered, so just need to report selection
                  triggerDateSelect(this.dragSelection, pev, this.component.context);
                  this.dragSelection = null;
              }
              else {
                  this.component.context.emitter.trigger('_noDateSelect');
              }
          };
          let { component } = settings;
          let { options } = component.context;
          let dragging = this.dragging = new FeaturefulElementDragging(settings.el);
          dragging.touchScrollAllowed = false;
          dragging.minDistance = options.selectMinDistance || 0;
          dragging.autoScroller.isEnabled = options.dragScroll;
          let hitDragging = this.hitDragging = new HitDragging(this.dragging, interactionSettingsToStore(settings));
          hitDragging.emitter.on('pointerdown', this.handlePointerDown);
          hitDragging.emitter.on('dragstart', this.handleDragStart);
          hitDragging.emitter.on('hitupdate', this.handleHitUpdate);
          hitDragging.emitter.on('pointerup', this.handlePointerUp);
      }
      destroy() {
          this.dragging.destroy();
      }
  }
  function getComponentTouchDelay$1(component) {
      let { options } = component.context;
      let delay = options.selectLongPressDelay;
      if (delay == null) {
          delay = options.longPressDelay;
      }
      return delay;
  }
  function joinHitsIntoSelection(hit0, hit1, dateSelectionTransformers) {
      let dateSpan0 = hit0.dateSpan;
      let dateSpan1 = hit1.dateSpan;
      // Only instant-aware components (currently timed timeline axes) may sort by instant, which
      // orders repeated civil times during DST fall-back correctly. For civil-only components,
      // deriving instants would reorder nonexistent spring-forward times (a civil 02:30 resolves
      // to instant 03:30, past a civil 03:00), so their edges must keep the civil marker sort.
      let hasInstants = dateSpan0.instantStartMs != null || dateSpan1.instantStartMs != null;
      let entries = [
          { date: dateSpan0.range.start, ms: getDateSpanInstantStartMs(dateSpan0, hit0.context.dateEnv) },
          { date: dateSpan0.range.end, ms: getDateSpanInstantEndMs(dateSpan0, hit0.context.dateEnv) },
          { date: dateSpan1.range.start, ms: getDateSpanInstantStartMs(dateSpan1, hit1.context.dateEnv) },
          { date: dateSpan1.range.end, ms: getDateSpanInstantEndMs(dateSpan1, hit1.context.dateEnv) },
      ];
      entries.sort(hasInstants
          ? (entry0, entry1) => compareNumbers(entry0.ms, entry1.ms)
          : (entry0, entry1) => compareNumbers(entry0.date.valueOf(), entry1.date.valueOf()));
      let props = {};
      for (let transformer of dateSelectionTransformers) {
          let res = transformer(hit0, hit1);
          if (res === false) {
              return null;
          }
          if (res) {
              Object.assign(props, res);
          }
      }
      if (hasInstants) {
          const validRange = buildValidInstanceRange({ marker: entries[0].date, instantMs: entries[0].ms }, { marker: entries[3].date, instantMs: entries[3].ms }, hit0.context.dateEnv);
          if (!validRange) {
              return null;
          }
          props.range = { start: validRange.start, end: validRange.end };
      }
      else {
          props.range = { start: entries[0].date, end: entries[3].date };
      }
      props.allDay = dateSpan0.allDay;
      if (hasInstants) {
          props.instantStartMs = entries[0].ms;
          props.instantEndMs = entries[3].ms;
      }
      return props;
  }

  /*
  When both hits come from an instant-aware component (their dateSpans carry exact instants),
  returns the drag distance in absolute ms. Otherwise null, and callers should fall back to
  civil-duration diffing.
  */
  function computeHitInstantDeltaMs(hit0, hit1) {
      const startMs0 = hit0.dateSpan.allDay ? null : hit0.dateSpan.instantStartMs;
      const startMs1 = hit1.dateSpan.allDay ? null : hit1.dateSpan.instantStartMs;
      if (startMs0 != null && startMs1 != null) {
          return startMs1 - startMs0;
      }
      return null;
  }
  function computeHitDelta(hit0, hit1, options = {}) {
      const instantDeltaMs = computeHitInstantDeltaMs(hit0, hit1);
      const date0 = options.date0 || hit0.dateSpan.range.start;
      const date1 = options.date1 || hit1.dateSpan.range.start;
      return {
          delta: instantDeltaMs != null
              ? createDuration(instantDeltaMs)
              : diffDates(date0, date1, hit0.context.dateEnv, options.largeUnit),
          instantDeltaMs,
      };
  }

  class EventDragging extends Interaction {
      constructor(settings) {
          super(settings);
          // internal state
          this.subjectEl = null;
          this.isDragging = false;
          this.eventRange = null;
          this.relevantEvents = null; // the events being dragged
          this.receivingContext = null;
          this.validMutation = null;
          this.mutatedRelevantEvents = null;
          this.handlePointerDown = (ev) => {
              let origTarget = ev.origEvent.target;
              let { component, dragging } = this;
              let { mirror } = dragging;
              let { options } = component.context;
              let initialContext = component.context;
              this.subjectEl = ev.subjectEl;
              let eventRange = this.eventRange = getElEventRange(ev.subjectEl);
              let eventInstanceId = eventRange.instance.instanceId;
              this.relevantEvents = getRelevantEvents(initialContext.getCurrentData().eventStore, eventInstanceId);
              dragging.minDistance = ev.isTouch ? 0 : options.eventDragMinDistance;
              dragging.delay =
                  // only do a touch delay if touch and this event hasn't been selected yet
                  (ev.isTouch && eventInstanceId !== component.props.eventSelection) ?
                      getComponentTouchDelay(component) :
                      null;
              mirror.parentNode = getAppendableRoot(origTarget);
              mirror.revertDuration = options.dragRevertDuration;
              mirror.colorScheme = options.colorScheme || '';
              let isValid = component.isValidSegDownEl(origTarget) &&
                  !origTarget.closest(`.${classNames.internalEventResizer}`); // NOT on a resizer
              if (!isValid) {
                  dragging.cancel();
              }
              else {
                  // disable dragging for elements that are resizable (ie, selectable)
                  // but are not draggable
                  // TODO: merge this with .cancel() ?
                  this.isDragging = ev.subjectEl
                      .classList.contains(classNames.internalEventDraggable);
              }
          };
          this.handleDragStart = (ev) => {
              let initialContext = this.component.context;
              let eventRange = this.eventRange;
              let eventInstanceId = eventRange.instance.instanceId;
              if (ev.isTouch) {
                  // need to select a different event?
                  if (eventInstanceId !== this.component.props.eventSelection) {
                      initialContext.dispatch({ type: 'SELECT_EVENT', eventInstanceId });
                  }
              }
              else {
                  // if now using mouse, but was previous touch interaction, clear selected event
                  initialContext.dispatch({ type: 'UNSELECT_EVENT' });
              }
              if (this.isDragging) {
                  initialContext.calendarApi.unselect(ev); // unselect *date* selection
                  initialContext.emitter.trigger('eventDragStart', {
                      el: this.subjectEl,
                      event: new EventImpl(initialContext, eventRange.def, eventRange.instance),
                      jsEvent: ev.origEvent, // Is this always a mouse event? See #4655
                      view: initialContext.viewApi,
                  });
              }
          };
          this.handleHitUpdate = (hit, isFinal) => {
              if (!this.isDragging) {
                  return;
              }
              let relevantEvents = this.relevantEvents;
              let initialHit = this.hitDragging.initialHit;
              let initialContext = this.component.context;
              // states based on new hit
              let receivingContext = null;
              let mutation = null;
              let mutatedRelevantEvents = null;
              let isInvalid = false;
              let interaction = {
                  affectedEvents: relevantEvents,
                  mutatedEvents: createEmptyEventStore(),
                  isEvent: true,
              };
              if (hit) {
                  receivingContext = hit.context;
                  let receivingOptions = receivingContext.options;
                  if (initialContext === receivingContext ||
                      (receivingOptions.editable && receivingOptions.droppable)) {
                      mutation = computeEventMutation(initialHit, hit, this.eventRange.instance.range.start, receivingContext.getCurrentData().pluginHooks.eventDragMutationMassagers);
                      if (mutation) {
                          mutatedRelevantEvents = applyMutationToEventStore(relevantEvents, receivingContext.getCurrentData().eventUiBases, mutation, receivingContext);
                          interaction.mutatedEvents = mutatedRelevantEvents;
                          if (!isInteractionValid(interaction, hit.dateProfile, receivingContext)) {
                              isInvalid = true;
                              mutation = null;
                              mutatedRelevantEvents = null;
                              interaction.mutatedEvents = createEmptyEventStore();
                          }
                      }
                  }
                  else {
                      receivingContext = null;
                  }
              }
              this.displayDrag(receivingContext, interaction);
              if (!isInvalid) {
                  enableCursor();
              }
              else {
                  disableCursor();
              }
              if (!isFinal) {
                  if (initialContext === receivingContext && // TODO: write test for this
                      isHitsEqual(initialHit, hit)) {
                      mutation = null;
                  }
                  this.dragging.setMirrorNeedsRevert(!mutation);
                  // render the mirror if no already-rendered mirror
                  // TODO: wish we could somehow wait for dispatch to guarantee render
                  this.dragging.setMirrorIsVisible(!hit || !this.subjectEl.getRootNode().querySelector(`.${classNames.internalEventMirror}`));
                  // assign states based on new hit
                  this.receivingContext = receivingContext;
                  this.validMutation = mutation;
                  this.mutatedRelevantEvents = mutatedRelevantEvents;
              }
          };
          this.handlePointerUp = () => {
              if (!this.isDragging) {
                  this.cleanup(); // because handleDragEnd won't fire
              }
          };
          this.handleDragEnd = (ev) => {
              if (this.isDragging) {
                  let initialContext = this.component.context;
                  let initialView = initialContext.viewApi;
                  let { receivingContext, validMutation } = this;
                  let eventDef = this.eventRange.def;
                  let eventInstance = this.eventRange.instance;
                  let eventApi = new EventImpl(initialContext, eventDef, eventInstance);
                  let relevantEvents = this.relevantEvents;
                  let mutatedRelevantEvents = this.mutatedRelevantEvents;
                  let { finalHit } = this.hitDragging;
                  this.clearDrag(); // must happen after revert animation
                  initialContext.emitter.trigger('eventDragStop', {
                      el: this.subjectEl,
                      event: eventApi,
                      jsEvent: ev.origEvent, // Is this always a mouse event? See #4655
                      view: initialView,
                  });
                  if (validMutation) {
                      // dropped within same calendar
                      if (receivingContext === initialContext) {
                          let updatedEventApi = new EventImpl(initialContext, mutatedRelevantEvents.defs[eventDef.defId], eventInstance ? mutatedRelevantEvents.instances[eventInstance.instanceId] : null);
                          initialContext.dispatch({
                              type: 'MERGE_EVENTS',
                              eventStore: mutatedRelevantEvents,
                          });
                          let eventChangeData = {
                              oldEvent: eventApi,
                              event: updatedEventApi,
                              relatedEvents: buildEventApis(mutatedRelevantEvents, initialContext, eventInstance),
                              revert() {
                                  initialContext.dispatch({
                                      type: 'MERGE_EVENTS',
                                      eventStore: relevantEvents, // the pre-change data
                                  });
                              },
                          };
                          let transformed = {};
                          for (let transformer of initialContext.getCurrentData().pluginHooks.eventDropTransformers) {
                              Object.assign(transformed, transformer(validMutation, initialContext));
                          }
                          initialContext.emitter.trigger('eventDrop', {
                              ...eventChangeData,
                              ...transformed,
                              el: ev.subjectEl,
                              delta: validMutation.datesDelta,
                              jsEvent: ev.origEvent, // bad
                              view: initialView,
                          });
                          initialContext.emitter.trigger('eventChange', eventChangeData);
                          // dropped in different calendar
                      }
                      else if (receivingContext) {
                          let eventRemoveData = {
                              event: eventApi,
                              relatedEvents: buildEventApis(relevantEvents, initialContext, eventInstance),
                              revert() {
                                  initialContext.dispatch({
                                      type: 'MERGE_EVENTS',
                                      eventStore: relevantEvents,
                                  });
                              },
                          };
                          initialContext.emitter.trigger('eventLeave', {
                              ...eventRemoveData,
                              draggedEl: ev.subjectEl,
                              view: initialView,
                          });
                          initialContext.dispatch({
                              type: 'REMOVE_EVENTS',
                              eventStore: relevantEvents,
                          });
                          initialContext.emitter.trigger('eventRemove', eventRemoveData);
                          let addedEventDef = mutatedRelevantEvents.defs[eventDef.defId];
                          let addedEventInstance = mutatedRelevantEvents.instances[eventInstance.instanceId];
                          let addedEventApi = new EventImpl(receivingContext, addedEventDef, addedEventInstance);
                          receivingContext.dispatch({
                              type: 'MERGE_EVENTS',
                              eventStore: mutatedRelevantEvents,
                          });
                          let eventAddData = {
                              event: addedEventApi,
                              relatedEvents: buildEventApis(mutatedRelevantEvents, receivingContext, addedEventInstance),
                              revert() {
                                  receivingContext.dispatch({
                                      type: 'REMOVE_EVENTS',
                                      eventStore: mutatedRelevantEvents,
                                  });
                              },
                          };
                          receivingContext.emitter.trigger('eventAdd', eventAddData);
                          if (ev.isTouch) {
                              receivingContext.dispatch({
                                  type: 'SELECT_EVENT',
                                  eventInstanceId: eventInstance.instanceId,
                              });
                          }
                          receivingContext.emitter.trigger('drop', {
                              ...buildDatePointApiWithContext(finalHit.dateSpan, receivingContext),
                              draggedEl: ev.subjectEl,
                              jsEvent: ev.origEvent, // Is this always a mouse event? See #4655
                              view: finalHit.context.viewApi,
                          });
                          receivingContext.emitter.trigger('eventReceive', {
                              ...eventAddData,
                              draggedEl: ev.subjectEl,
                              view: finalHit.context.viewApi,
                          });
                      }
                  }
                  else {
                      initialContext.emitter.trigger('_noEventDrop');
                  }
              }
              this.cleanup();
          };
          let { component } = this;
          let { options } = component.context;
          let dragging = this.dragging = new FeaturefulElementDragging(settings.el);
          dragging.pointer.selector = EventDragging.SELECTOR;
          dragging.touchScrollAllowed = false;
          dragging.autoScroller.isEnabled = options.dragScroll;
          let hitDragging = this.hitDragging = new HitDragging(this.dragging, interactionSettingsStore);
          hitDragging.useSubjectCenter = settings.useEventCenter;
          hitDragging.emitter.on('pointerdown', this.handlePointerDown);
          hitDragging.emitter.on('dragstart', this.handleDragStart);
          hitDragging.emitter.on('hitupdate', this.handleHitUpdate);
          hitDragging.emitter.on('pointerup', this.handlePointerUp);
          hitDragging.emitter.on('dragend', this.handleDragEnd);
      }
      destroy() {
          this.dragging.destroy();
      }
      // render a drag state on the next receivingCalendar
      displayDrag(nextContext, state) {
          let initialContext = this.component.context;
          let prevContext = this.receivingContext;
          // does the previous calendar need to be cleared?
          if (prevContext && prevContext !== nextContext) {
              // does the initial calendar need to be cleared?
              // if so, don't clear all the way. we still need to to hide the affectedEvents
              if (prevContext === initialContext) {
                  prevContext.dispatch({
                      type: 'SET_EVENT_DRAG',
                      state: {
                          affectedEvents: state.affectedEvents,
                          mutatedEvents: createEmptyEventStore(),
                          isEvent: true,
                      },
                  });
                  // completely clear the old calendar if it wasn't the initial
              }
              else {
                  prevContext.dispatch({ type: 'UNSET_EVENT_DRAG' });
              }
          }
          if (nextContext) {
              nextContext.dispatch({ type: 'SET_EVENT_DRAG', state });
          }
      }
      clearDrag() {
          let initialCalendar = this.component.context;
          let { receivingContext } = this;
          if (receivingContext) {
              receivingContext.dispatch({ type: 'UNSET_EVENT_DRAG' });
          }
          // the initial calendar might have an dummy drag state from displayDrag
          if (initialCalendar !== receivingContext) {
              initialCalendar.dispatch({ type: 'UNSET_EVENT_DRAG' });
          }
      }
      cleanup() {
          this.isDragging = false;
          this.eventRange = null;
          this.relevantEvents = null;
          this.receivingContext = null;
          this.validMutation = null;
          this.mutatedRelevantEvents = null;
      }
  }
  // TODO: test this in IE11
  // QUESTION: why do we need it on the resizable???
  EventDragging.SELECTOR = `.${classNames.internalEventDraggable}, .${classNames.internalEventResizable}`;
  function computeEventMutation(hit0, hit1, eventInstanceStart, massagers) {
      let dateSpan0 = hit0.dateSpan;
      let dateSpan1 = hit1.dateSpan;
      let date0 = dateSpan0.range.start;
      let date1 = dateSpan1.range.start;
      let standardProps = {};
      if (dateSpan0.allDay !== dateSpan1.allDay) {
          standardProps.allDay = dateSpan1.allDay;
          standardProps.hasEnd = hit1.context.options.allDayMaintainDuration;
          if (dateSpan1.allDay) {
              // means date1 is already start-of-day,
              // but date0 needs to be converted
              date0 = startOfDay(eventInstanceStart);
          }
          else {
              // Moving from allDate->timed
              // Doesn't matter where on the event the drag began, mutate the event's start-date to date1
              date0 = eventInstanceStart;
          }
      }
      const { delta, instantDeltaMs } = computeHitDelta(hit0, hit1, {
          date0,
          date1,
          largeUnit: hit0.componentId === hit1.componentId ? hit0.largeUnit : null,
      });
      if (delta.milliseconds) { // has hours/minutes/seconds
          standardProps.allDay = false;
      }
      let mutation = {
          datesDelta: delta,
          ...(instantDeltaMs != null ? { instantDatesDeltaMs: instantDeltaMs } : {}),
          standardProps,
      };
      for (let massager of massagers) {
          massager(mutation, hit0, hit1);
      }
      return mutation;
  }
  function getComponentTouchDelay(component) {
      let { options } = component.context;
      let delay = options.eventLongPressDelay;
      if (delay == null) {
          delay = options.longPressDelay;
      }
      return delay;
  }

  class EventResizing extends Interaction {
      constructor(settings) {
          super(settings);
          // internal state
          this.draggingSegEl = null;
          this.draggingEventRange = null; // TODO: rename to resizingSeg? subjectSeg?
          this.eventRange = null;
          this.relevantEvents = null;
          this.validMutation = null;
          this.mutatedRelevantEvents = null;
          this.handlePointerDown = (ev) => {
              let { component } = this;
              let segEl = this.querySegEl(ev);
              let eventRange = this.eventRange = getElEventRange(segEl);
              this.dragging.minDistance = component.context.options.eventDragMinDistance;
              const isValid = this.component.isValidSegDownEl(ev.origEvent.target) &&
                  !(ev.isTouch && this.component.props.eventSelection !== eventRange.instance.instanceId);
              if (!isValid) {
                  this.dragging.cancel();
              }
          };
          this.handleDragStart = (ev) => {
              let { context } = this.component;
              let eventRange = this.eventRange;
              this.relevantEvents = getRelevantEvents(context.getCurrentData().eventStore, this.eventRange.instance.instanceId);
              let segEl = this.querySegEl(ev);
              this.draggingSegEl = segEl;
              this.draggingEventRange = getElEventRange(segEl);
              context.calendarApi.unselect();
              context.emitter.trigger('eventResizeStart', {
                  el: segEl,
                  event: new EventImpl(context, eventRange.def, eventRange.instance),
                  jsEvent: ev.origEvent, // Is this always a mouse event? See #4655
                  view: context.viewApi,
              });
          };
          this.handleHitUpdate = (hit, isFinal, ev) => {
              let { context } = this.component;
              let relevantEvents = this.relevantEvents;
              let initialHit = this.hitDragging.initialHit;
              let eventInstance = this.eventRange.instance;
              let mutation = null;
              let mutatedRelevantEvents = null;
              let isInvalid = false;
              let interaction = {
                  affectedEvents: relevantEvents,
                  mutatedEvents: createEmptyEventStore(),
                  isEvent: true,
              };
              if (hit) {
                  let disallowed = hit.componentId === initialHit.componentId
                      && this.isHitComboAllowed
                      && !this.isHitComboAllowed(initialHit, hit);
                  if (!disallowed) {
                      mutation = computeMutation(initialHit, hit, ev.subjectEl.classList.contains(classNames.internalEventResizerStart), eventInstance.range);
                  }
              }
              if (mutation) {
                  mutatedRelevantEvents = applyMutationToEventStore(relevantEvents, context.getCurrentData().eventUiBases, mutation, context);
                  interaction.mutatedEvents = mutatedRelevantEvents;
                  if (!isInteractionValid(interaction, hit.dateProfile, context)) {
                      isInvalid = true;
                      mutation = null;
                      mutatedRelevantEvents = null;
                      interaction.mutatedEvents = null;
                  }
              }
              if (mutatedRelevantEvents) {
                  context.dispatch({
                      type: 'SET_EVENT_RESIZE',
                      state: interaction,
                  });
              }
              else {
                  context.dispatch({ type: 'UNSET_EVENT_RESIZE' });
              }
              if (!isInvalid) {
                  enableCursor();
              }
              else {
                  disableCursor();
              }
              if (!isFinal) {
                  if (mutation && isHitsEqual(initialHit, hit)) {
                      mutation = null;
                  }
                  this.validMutation = mutation;
                  this.mutatedRelevantEvents = mutatedRelevantEvents;
              }
          };
          this.handleDragEnd = (ev) => {
              let { context } = this.component;
              let eventDef = this.eventRange.def;
              let eventInstance = this.eventRange.instance;
              let eventApi = new EventImpl(context, eventDef, eventInstance);
              let relevantEvents = this.relevantEvents;
              let mutatedRelevantEvents = this.mutatedRelevantEvents;
              context.emitter.trigger('eventResizeStop', {
                  el: this.draggingSegEl,
                  event: eventApi,
                  jsEvent: ev.origEvent, // Is this always a mouse event? See #4655
                  view: context.viewApi,
              });
              if (this.validMutation) {
                  let updatedEventApi = new EventImpl(context, mutatedRelevantEvents.defs[eventDef.defId], eventInstance ? mutatedRelevantEvents.instances[eventInstance.instanceId] : null);
                  context.dispatch({
                      type: 'MERGE_EVENTS',
                      eventStore: mutatedRelevantEvents,
                  });
                  let eventChangeData = {
                      oldEvent: eventApi,
                      event: updatedEventApi,
                      relatedEvents: buildEventApis(mutatedRelevantEvents, context, eventInstance),
                      revert() {
                          context.dispatch({
                              type: 'MERGE_EVENTS',
                              eventStore: relevantEvents, // the pre-change events
                          });
                      },
                  };
                  context.emitter.trigger('eventResize', {
                      ...eventChangeData,
                      el: this.draggingSegEl,
                      startDelta: this.validMutation.startDelta || createDuration(0),
                      endDelta: this.validMutation.endDelta || createDuration(0),
                      jsEvent: ev.origEvent,
                      view: context.viewApi,
                  });
                  context.emitter.trigger('eventChange', eventChangeData);
              }
              else {
                  context.emitter.trigger('_noEventResize');
              }
              // reset all internal state
              this.draggingEventRange = null;
              this.relevantEvents = null;
              this.validMutation = null;
              // okay to keep eventInstance around. useful to set it in handlePointerDown
          };
          let { component } = settings;
          let dragging = this.dragging = new FeaturefulElementDragging(settings.el);
          dragging.pointer.selector = `.${classNames.internalEventResizer}`;
          dragging.touchScrollAllowed = false;
          dragging.autoScroller.isEnabled = component.context.options.dragScroll;
          let hitDragging = this.hitDragging = new HitDragging(this.dragging, interactionSettingsToStore(settings));
          hitDragging.emitter.on('pointerdown', this.handlePointerDown);
          hitDragging.emitter.on('dragstart', this.handleDragStart);
          hitDragging.emitter.on('hitupdate', this.handleHitUpdate);
          hitDragging.emitter.on('dragend', this.handleDragEnd);
      }
      destroy() {
          this.dragging.destroy();
      }
      querySegEl(ev) {
          return ev.subjectEl.closest(`.${classNames.internalEvent}`);
      }
  }
  function computeMutation(hit0, hit1, isFromStart, instanceRange) {
      const { context } = hit0;
      let date0 = hit0.dateSpan.range.start;
      let date1 = hit1.dateSpan.range.start;
      const { delta, instantDeltaMs } = computeHitDelta(hit0, hit1, {
          date0,
          date1,
          largeUnit: hit0.largeUnit,
      });
      // validate with the SAME baseline the mutation will apply with (addDeltaToRangeEdge
      // bases instant deltas off the edge's stored instant). on the exact path, real-time
      // order is the truth — the mutation re-expresses fold-compressed civil markers itself
      if (isFromStart) {
          const newStart = addDeltaToRangeEdge(instanceRange.start, instanceRange.instantStartMs, delta, instantDeltaMs ?? undefined, context);
          if (newStart.instantMs != null
              ? newStart.instantMs < getRangeInstantEndMs(instanceRange, context.dateEnv)
              : newStart.marker < instanceRange.end) {
              return {
                  startDelta: delta,
                  ...(instantDeltaMs != null ? { instantStartDeltaMs: instantDeltaMs } : {}),
              };
          }
      }
      else {
          const newEnd = addDeltaToRangeEdge(instanceRange.end, instanceRange.instantEndMs, delta, instantDeltaMs ?? undefined, context);
          if (newEnd.instantMs != null
              ? newEnd.instantMs > getRangeInstantStartMs(instanceRange, context.dateEnv)
              : newEnd.marker > instanceRange.start) {
              return {
                  endDelta: delta,
                  ...(instantDeltaMs != null ? { instantEndDeltaMs: instantDeltaMs } : {}),
              };
          }
      }
      return null;
  }

  class UnselectAuto {
      constructor(context) {
          this.context = context;
          this.isRecentPointerDateSelect = false; // wish we could use a selector to detect date selection, but uses hit system
          this.matchesCancel = false;
          this.matchesEvent = false;
          this.onSelect = (selectInfo) => {
              if (selectInfo.jsEvent) {
                  this.isRecentPointerDateSelect = true;
              }
          };
          this.onDocumentPointerDown = (pev) => {
              let unselectCancel = this.context.options.unselectCancel;
              let downEl = getEventTargetViaRoot(pev.origEvent);
              this.matchesCancel = !!downEl.closest(unselectCancel);
              this.matchesEvent = !!downEl.closest(EventDragging.SELECTOR); // interaction started on an event?
          };
          this.onDocumentPointerUp = (pev) => {
              let { context } = this;
              let { documentPointer } = this;
              let calendarState = context.getCurrentData();
              // touch-scrolling should never unfocus any type of selection
              if (!documentPointer.wasTouchScroll) {
                  if (calendarState.dateSelection && // an existing date selection?
                      !this.isRecentPointerDateSelect // a new pointer-initiated date selection since last onDocumentPointerUp?
                  ) {
                      let unselectAuto = context.options.unselectAuto;
                      if (unselectAuto && (!unselectAuto || !this.matchesCancel)) {
                          context.calendarApi.unselect(pev);
                      }
                  }
                  if (calendarState.eventSelection && // an existing event selected?
                      !this.matchesEvent // interaction DIDN'T start on an event
                  ) {
                      context.dispatch({ type: 'UNSELECT_EVENT' });
                  }
              }
              this.isRecentPointerDateSelect = false;
          };
          let documentPointer = this.documentPointer = new PointerDragging(document);
          documentPointer.shouldIgnoreMove = true;
          documentPointer.shouldWatchScroll = false;
          documentPointer.emitter.on('pointerdown', this.onDocumentPointerDown);
          documentPointer.emitter.on('pointerup', this.onDocumentPointerUp);
          /*
          TODO: better way to know about whether there was a selection with the pointer
          */
          context.emitter.on('select', this.onSelect);
      }
      destroy() {
          this.context.emitter.off('select', this.onSelect);
          this.documentPointer.destroy();
      }
  }

  var interactionPlugin = {
      name: 'interaction',
      componentInteractions: [DateClicking, DateSelecting, EventDragging, EventResizing],
      calendarInteractions: [UnselectAuto],
      elementDraggingImpl: FeaturefulElementDragging,
  };

  /*
  Information about what will happen when an external element is dragged-and-dropped
  onto a calendar. Contains information for creating an event.
  */
  const DRAG_META_REFINERS = {
      startTime: createDuration,
      duration: createDuration,
      create: Boolean,
      sourceId: String,
  };
  function parseDragMeta(raw) {
      let { refined, extra } = refineProps(raw, DRAG_META_REFINERS);
      return {
          startTime: refined.startTime || null,
          duration: refined.duration || null,
          create: refined.create != null ? refined.create : true,
          sourceId: refined.sourceId,
          leftoverProps: extra,
      };
  }

  /*
  Given an already instantiated draggable object for one-or-more elements,
  Interprets any dragging as an attempt to drag an events that lives outside
  of a calendar onto a calendar.
  */
  class ExternalElementDragging {
      constructor(dragging, suppliedDragMeta) {
          this.receivingContext = null;
          this.droppableEvent = null; // will exist for all drags, even if create:false
          this.suppliedDragMeta = null;
          this.dragMeta = null;
          this.handleDragStart = (ev) => {
              this.dragMeta = this.buildDragMeta(ev.subjectEl);
          };
          this.handleHitUpdate = (hit, isFinal, ev) => {
              let { dragging } = this.hitDragging;
              let receivingContext = null;
              let droppableEvent = null;
              let isInvalid = false;
              let interaction = {
                  affectedEvents: createEmptyEventStore(),
                  mutatedEvents: createEmptyEventStore(),
                  isEvent: this.dragMeta.create,
              };
              if (hit) {
                  receivingContext = hit.context;
                  if (this.canDropElOnCalendar(ev.subjectEl, receivingContext)) {
                      droppableEvent = computeEventForDateSpan(hit.dateSpan, this.dragMeta, receivingContext);
                      interaction.mutatedEvents = eventTupleToStore(droppableEvent);
                      isInvalid = !isInteractionValid(interaction, hit.dateProfile, receivingContext);
                      if (isInvalid) {
                          interaction.mutatedEvents = createEmptyEventStore();
                          droppableEvent = null;
                      }
                  }
              }
              this.displayDrag(receivingContext, interaction);
              // show mirror if no already-rendered mirror element OR if we are shutting down the mirror (?)
              // TODO: wish we could somehow wait for dispatch to guarantee render
              dragging.setMirrorIsVisible(isFinal ||
                  !droppableEvent ||
                  !document.querySelector(`.${classNames.internalEventMirror}`));
              if (!isInvalid) {
                  enableCursor();
              }
              else {
                  disableCursor();
              }
              if (!isFinal) {
                  dragging.setMirrorNeedsRevert(!droppableEvent);
                  this.receivingContext = receivingContext;
                  this.droppableEvent = droppableEvent;
              }
          };
          this.handleDragEnd = (pev) => {
              let { receivingContext, droppableEvent } = this;
              this.clearDrag();
              if (receivingContext && droppableEvent) {
                  let finalHit = this.hitDragging.finalHit;
                  let finalView = finalHit.context.viewApi;
                  let dragMeta = this.dragMeta;
                  receivingContext.emitter.trigger('drop', {
                      ...buildDatePointApiWithContext(finalHit.dateSpan, receivingContext),
                      draggedEl: pev.subjectEl,
                      jsEvent: pev.origEvent, // Is this always a mouse event? See #4655
                      view: finalView,
                  });
                  if (dragMeta.create) {
                      let addingEvents = eventTupleToStore(droppableEvent);
                      receivingContext.dispatch({
                          type: 'MERGE_EVENTS',
                          eventStore: addingEvents,
                      });
                      if (pev.isTouch) {
                          receivingContext.dispatch({
                              type: 'SELECT_EVENT',
                              eventInstanceId: droppableEvent.instance.instanceId,
                          });
                      }
                      // signal that an external event landed
                      receivingContext.emitter.trigger('eventReceive', {
                          event: new EventImpl(receivingContext, droppableEvent.def, droppableEvent.instance),
                          relatedEvents: [],
                          revert() {
                              receivingContext.dispatch({
                                  type: 'REMOVE_EVENTS',
                                  eventStore: addingEvents,
                              });
                          },
                          draggedEl: pev.subjectEl,
                          view: finalView,
                      });
                  }
              }
              this.receivingContext = null;
              this.droppableEvent = null;
          };
          let hitDragging = this.hitDragging = new HitDragging(dragging, interactionSettingsStore);
          hitDragging.requireInitial = false; // will start outside of a component
          hitDragging.emitter.on('dragstart', this.handleDragStart);
          hitDragging.emitter.on('hitupdate', this.handleHitUpdate);
          hitDragging.emitter.on('dragend', this.handleDragEnd);
          this.suppliedDragMeta = suppliedDragMeta;
      }
      buildDragMeta(subjectEl) {
          if (typeof this.suppliedDragMeta === 'object') {
              return parseDragMeta(this.suppliedDragMeta);
          }
          if (typeof this.suppliedDragMeta === 'function') {
              return parseDragMeta(this.suppliedDragMeta(subjectEl));
          }
          return getDragMetaFromEl(subjectEl);
      }
      displayDrag(nextContext, state) {
          let prevContext = this.receivingContext;
          if (prevContext && prevContext !== nextContext) {
              prevContext.dispatch({ type: 'UNSET_EVENT_DRAG' });
          }
          if (nextContext) {
              nextContext.dispatch({ type: 'SET_EVENT_DRAG', state });
          }
      }
      clearDrag() {
          if (this.receivingContext) {
              this.receivingContext.dispatch({ type: 'UNSET_EVENT_DRAG' });
          }
      }
      canDropElOnCalendar(el, receivingContext) {
          let dropAccept = receivingContext.options.dropAccept;
          if (typeof dropAccept === 'function') {
              return dropAccept.call(receivingContext.calendarApi, el);
          }
          if (typeof dropAccept === 'string' && dropAccept) {
              return el.matches(dropAccept);
          }
          return true;
      }
  }
  // Utils for computing event store from the DragMeta
  // ----------------------------------------------------------------------------------------------------
  function computeEventForDateSpan(dateSpan, dragMeta, context) {
      let defProps = { ...dragMeta.leftoverProps };
      for (let transform of context.pluginHooks.externalDefTransforms) {
          Object.assign(defProps, transform(dateSpan, dragMeta));
      }
      let { refined, extra } = refineEventDef(defProps, context);
      let def = parseEventDef(refined, extra, dragMeta.sourceId, dateSpan.allDay, context.options.forceEventDuration || Boolean(dragMeta.duration), // hasEnd
      context);
      let start = dateSpan.range.start;
      // only rely on time info if drop zone is all-day,
      // otherwise, we already know the time
      if (dateSpan.allDay && dragMeta.startTime) {
          start = context.dateEnv.add(start, dragMeta.startTime);
      }
      // carry the drop span's exact instant when the start marker was used as-is
      // (keeps identity during DST fall-back doubled slots)
      let startEdge = {
          marker: start,
          instantMs: !dateSpan.allDay ? dateSpan.instantStartMs : undefined,
      };
      // an exact start yields an exact derived end (real elapsed duration)
      let endEdge = dragMeta.duration ?
          addDurationToEdge(startEdge, dragMeta.duration, context.dateEnv) :
          getDefaultEventEndEdge(dateSpan.allDay, startEdge, context);
      let instance = createEventInstance(def.defId, buildEventInstanceRange(startEdge.marker, endEdge.marker, startEdge.instantMs, endEdge.instantMs));
      return { def, instance };
  }
  // Utils for extracting data from element
  // ----------------------------------------------------------------------------------------------------
  function getDragMetaFromEl(el) {
      let str = getEmbeddedElData(el, 'event');
      let obj = str ?
          JSON.parse(str) :
          { create: false }; // if no embedded data, assume no event creation
      return parseDragMeta(obj);
  }
  config.dataAttrPrefix = '';
  function getEmbeddedElData(el, name) {
      let prefix = config.dataAttrPrefix;
      let prefixedName = (prefix ? prefix + '-' : '') + name;
      return el.getAttribute('data-' + prefixedName) || '';
  }

  /*
  Detects when a *THIRD-PARTY* drag-n-drop system interacts with elements.
  The third-party system is responsible for drawing the visuals effects of the drag.
  This class simply monitors for pointer movements and fires events.
  It also has the ability to hide the moving element (the "mirror") during the drag.
  */
  class InferredElementDragging extends ElementDragging {
      constructor(containerEl) {
          super(containerEl);
          this.shouldIgnoreMove = false;
          this.mirrorSelector = '';
          this.currentMirrorEl = null;
          this.handlePointerDown = (ev) => {
              this.emitter.trigger('pointerdown', ev);
              if (!this.shouldIgnoreMove) {
                  // fire dragstart right away. does not support delay or min-distance
                  this.emitter.trigger('dragstart', ev);
              }
          };
          this.handlePointerMove = (ev) => {
              if (!this.shouldIgnoreMove) {
                  this.emitter.trigger('dragmove', ev);
              }
          };
          this.handlePointerUp = (ev) => {
              this.emitter.trigger('pointerup', ev);
              if (!this.shouldIgnoreMove) {
                  // fire dragend right away. does not support a revert animation
                  this.emitter.trigger('dragend', ev);
              }
          };
          let pointer = this.pointer = new PointerDragging(containerEl);
          pointer.emitter.on('pointerdown', this.handlePointerDown);
          pointer.emitter.on('pointermove', this.handlePointerMove);
          pointer.emitter.on('pointerup', this.handlePointerUp);
      }
      destroy() {
          this.pointer.destroy();
      }
      cancel() {
          this.shouldIgnoreMove = true;
      }
      setMirrorIsVisible(bool) {
          if (bool) {
              // restore a previously hidden element.
              // use the reference in case the selector class has already been removed.
              if (this.currentMirrorEl) {
                  this.currentMirrorEl.style.visibility = '';
                  this.currentMirrorEl = null;
              }
          }
          else {
              let mirrorEl = this.mirrorSelector
                  // TODO: somehow query FullCalendars WITHIN shadow-roots
                  ? document.querySelector(this.mirrorSelector)
                  : null;
              if (mirrorEl) {
                  this.currentMirrorEl = mirrorEl;
                  mirrorEl.style.visibility = 'hidden';
              }
          }
      }
  }

  /*
  Bridges third-party drag-n-drop systems with FullCalendar.
  Must be instantiated and destroyed by caller.
  */
  class ThirdPartyDraggable {
      constructor(containerOrSettings, settings) {
          let containerEl = document;
          if (
          // wish we could just test instanceof EventTarget, but doesn't work in IE11
          containerOrSettings === document ||
              containerOrSettings instanceof Element) {
              containerEl = containerOrSettings;
              settings = settings || {};
          }
          else {
              settings = (containerOrSettings || {});
          }
          let dragging = this.dragging = new InferredElementDragging(containerEl);
          if (typeof settings.itemSelector === 'string') {
              dragging.pointer.selector = settings.itemSelector;
          }
          else if (containerEl === document) {
              dragging.pointer.selector = '[data-event]';
          }
          if (typeof settings.mirrorSelector === 'string') {
              dragging.mirrorSelector = settings.mirrorSelector;
          }
          let externalDragging = new ExternalElementDragging(dragging, settings.eventData);
          // The hit-detection system requires that the dnd-mirror-element be pointer-events:none,
          // but this can't be guaranteed for third-party draggables, so disable
          externalDragging.hitDragging.disablePointCheck = true;
      }
      destroy() {
          this.dragging.destroy();
      }
  }

  /*
  Makes an element (that is *external* to any calendar) draggable.
  Can pass in data that determines how an event will be created when dropped onto a calendar.
  Leverages FullCalendar's internal drag-n-drop functionality WITHOUT a third-party drag system.
  */
  class ExternalDraggable {
      constructor(el, settings = {}) {
          this.handlePointerDown = (ev) => {
              let { dragging } = this;
              let { minDistance, longPressDelay } = this.settings;
              dragging.minDistance =
                  minDistance != null ?
                      minDistance :
                      (ev.isTouch ? 0 : BASE_OPTION_DEFAULTS.eventDragMinDistance);
              dragging.delay =
                  ev.isTouch ? // TODO: eventually read eventLongPressDelay instead vvv
                      (longPressDelay != null ? longPressDelay : BASE_OPTION_DEFAULTS.longPressDelay) :
                      0;
          };
          this.handleDragStart = (ev) => {
              if (ev.isTouch &&
                  this.dragging.delay &&
                  ev.subjectEl.classList.contains(classNames.internalEvent)) {
                  this.dragging.mirror.getMirrorEl().classList.add(classNames.internalEventSelected);
              }
          };
          this.settings = settings;
          let dragging = this.dragging = new FeaturefulElementDragging(el);
          dragging.touchScrollAllowed = false;
          if (settings.itemSelector != null) {
              dragging.pointer.selector = settings.itemSelector;
          }
          if (settings.appendTo != null) {
              dragging.mirror.parentNode = settings.appendTo; // TODO: write tests
          }
          dragging.emitter.on('pointerdown', this.handlePointerDown);
          dragging.emitter.on('dragstart', this.handleDragStart);
          new ExternalElementDragging(dragging, settings.eventData); // eslint-disable-line no-new
      }
      destroy() {
          this.dragging.destroy();
      }
  }

  var interaction = /*#__PURE__*/Object.freeze({
      __proto__: null,
      Draggable: ExternalDraggable,
      ThirdPartyDraggable: ThirdPartyDraggable,
      'default': interactionPlugin
  });

  class TableDateProfileGenerator extends DateProfileGenerator {
      // Computes the date range that will be rendered
      buildRenderRange(currentRange, currentRangeUnit, isRangeAllDay) {
          let renderRange = super.buildRenderRange(currentRange, currentRangeUnit, isRangeAllDay);
          let { props } = this;
          return buildDayTableRenderRange({
              currentRange: renderRange, // ???
              snapToWeek: /^(year|month)$/.test(currentRangeUnit),
              fixedWeekCount: props.fixedWeekCount,
              dateEnv: props.dateEnv,
          });
      }
  }
  function buildDayTableRenderRange(props) {
      let { dateEnv, currentRange } = props;
      let { start, end } = currentRange;
      let endOfWeek;
      // year and month views should be aligned with weeks. this is already done for week
      if (props.snapToWeek) {
          start = dateEnv.startOfWeek(start);
          // make end-of-week if not already
          endOfWeek = dateEnv.startOfWeek(end);
          if (endOfWeek.valueOf() !== end.valueOf()) {
              end = addWeeks(endOfWeek, 1);
          }
      }
      // ensure 6 weeks
      if (props.fixedWeekCount) {
          // TODO: instead of these date-math gymnastics (for multimonth view),
          // compute dateprofiles of all months, then use start of first and end of last.
          let lastMonthRenderStart = dateEnv.startOfWeek(dateEnv.startOfMonth(addDays(currentRange.end, -1)));
          let rowCount = Math.ceil(// could be partial weeks due to hiddenDays
          diffWeeks(lastMonthRenderStart, end));
          end = addWeeks(end, 6 - rowCount);
      }
      return { start, end };
  }

  class DayGridView extends BaseComponent {
      constructor() {
          super(...arguments);
          // memo
          this.buildDayTableModel = memoize(buildDayTableModel);
          this.buildDateRowConfigs = memoize(buildDateRowConfigs);
          this.createDayHeaderFormatter = memoize(createDayHeaderFormatter);
          // internal
          this.slicer = new DayTableSlicer();
      }
      render() {
          const { props, context } = this;
          const { dateProfile } = props;
          const { options, dateEnv } = context;
          const dayTableModel = this.buildDayTableModel(dateProfile, context.dateProfileGenerator, dateEnv);
          const datesRepDistinctDays = dayTableModel.rowCount === 1;
          const dayHeaderFormat = this.createDayHeaderFormatter(context.options.dayHeaderFormat, datesRepDistinctDays, dayTableModel.colCount);
          const slicedProps = this.slicer.sliceProps(props, dateProfile, options.nextDayThreshold, context, dayTableModel);
          return (u$1(NowTimer, { unit: "day", children: (nowDate, todayRange) => {
                  const headerTiers = this.buildDateRowConfigs(dayTableModel.headerDates, datesRepDistinctDays, dateProfile, todayRange, dayHeaderFormat, context);
                  return (u$1(DayGridLayout, { labelId: props.labelId, labelStr: props.labelStr, dateProfile: dateProfile, todayRange: todayRange, cellRows: dayTableModel.cellRows, forPrint: props.forPrint, className: props.className, 
                      // header content
                      headerTiers: headerTiers, 
                      // body content
                      fgEventSegs: slicedProps.fgEventSegs, bgEventSegs: slicedProps.bgEventSegs, businessHourSegs: slicedProps.businessHourSegs, dateSelectionSegs: slicedProps.dateSelectionSegs, eventDrag: slicedProps.eventDrag, eventResize: slicedProps.eventResize, eventSelection: slicedProps.eventSelection }));
              } }));
      }
  }

  var dayGridPlugin = {
      name: 'daygrid',
      initialView: 'dayGridMonth',
      views: {
          dayGrid: {
              component: DayGridView,
              dateProfileGeneratorClass: TableDateProfileGenerator,
          },
          dayGridDay: {
              type: 'dayGrid',
              duration: { days: 1 },
          },
          dayGridWeek: {
              type: 'dayGrid',
              duration: { weeks: 1 },
          },
          dayGridMonth: {
              type: 'dayGrid',
              duration: { months: 1 },
              fixedWeekCount: true,
          },
          dayGridYear: {
              type: 'dayGrid',
              duration: { years: 1 },
          },
      },
  };

  var daygrid = /*#__PURE__*/Object.freeze({
      __proto__: null,
      'default': dayGridPlugin
  });

  class TimeGridView extends DateComponent {
      constructor() {
          super(...arguments);
          // memo
          this.createDayHeaderFormatter = memoize(createDayHeaderFormatter);
          this.buildDaySeries = memoize((dateProfile, dateProfileGenerator) => (new DaySeriesModel(dateProfile.renderRange, dateProfileGenerator)));
          this.buildDayCols = memoize(buildDayColsFromSeries);
          this.extractColDates = memoize((cols) => cols.map((col) => col.date));
          this.extractColRanges = memoize((cols) => cols.map((col) => col.range));
          this.buildDateRowConfigs = memoize(buildDateRowConfigs);
          this.splitFgEventSegs = memoize((organizeSegsByCol));
          this.splitBgEventSegs = memoize((organizeSegsByCol));
          this.splitBusinessHourSegs = memoize((organizeSegsByCol));
          this.splitNowIndicatorSegs = memoize((organizeSegsByCol));
          this.splitDateSelectionSegs = memoize((organizeSegsByCol));
          this.splitEventDrag = memoize(splitInteractionByCol);
          this.splitEventResize = memoize(splitInteractionByCol);
          // internal
          this.allDaySplitter = new AllDaySplitter();
          this.daySeriesSlicer = new DaySeriesSlicer();
          this.dayTimeColsSlicer = new DayTimeColsSlicer();
      }
      render() {
          const { props, context } = this;
          const { dateProfile } = props;
          const { options, dateProfileGenerator } = context;
          const daySeries = this.buildDaySeries(dateProfile, dateProfileGenerator);
          const cols = this.buildDayCols(daySeries, context.dateEnv, {
              slotRange: dateProfile,
              activeRange: dateProfile.activeRange,
          });
          const colDates = this.extractColDates(cols);
          const dayRanges = this.extractColRanges(cols);
          const splitProps = this.allDaySplitter.splitProps(props);
          const allDayProps = this.daySeriesSlicer.sliceProps(splitProps.allDay, dateProfile, options.nextDayThreshold, context, daySeries);
          const timedProps = this.dayTimeColsSlicer.sliceProps(splitProps.timed, dateProfile, null, context, dayRanges);
          const dayHeaderFormat = this.createDayHeaderFormatter(context.options.dayHeaderFormat, true, // datesRepDistinctDays
          cols.length);
          return (u$1(NowTimer, { unit: options.nowIndicator ? 'minute' : 'day' /* hacky */, children: (nowDate, todayRange, nowMs) => {
                  const colCount = cols.length;
                  const nowIndicatorSeg = !props.forPrint && options.nowIndicator &&
                      this.dayTimeColsSlicer.sliceNowDate(nowDate, dateProfile, options.nextDayThreshold, context, dayRanges);
                  const fgEventSegsByCol = this.splitFgEventSegs(timedProps.fgEventSegs, colCount);
                  const bgEventSegsByCol = this.splitBgEventSegs(timedProps.bgEventSegs, colCount);
                  const businessHourSegsByCol = this.splitBusinessHourSegs(timedProps.businessHourSegs, colCount);
                  const nowIndicatorSegsByCol = this.splitNowIndicatorSegs(nowIndicatorSeg, colCount);
                  const dateSelectionSegsByCol = this.splitDateSelectionSegs(timedProps.dateSelectionSegs, colCount);
                  const eventDragByCol = this.splitEventDrag(timedProps.eventDrag, colCount);
                  const eventResizeByCol = this.splitEventResize(timedProps.eventResize, colCount);
                  const headerTiers = this.buildDateRowConfigs(colDates, true, // datesRepDistinctDays
                  props.dateProfile, todayRange, dayHeaderFormat, context);
                  return (u$1(TimeGridLayout, { labelId: props.labelId, labelStr: props.labelStr, dateProfile: dateProfile, nowDate: nowDate, nowMs: nowMs, todayRange: todayRange, cells: cols, forPrint: props.forPrint, className: props.className, 
                      // header content
                      headerTiers: headerTiers, 
                      // all-day content
                      fgEventSegs: allDayProps.fgEventSegs, bgEventSegs: allDayProps.bgEventSegs, businessHourSegs: allDayProps.businessHourSegs, dateSelectionSegs: allDayProps.dateSelectionSegs, eventDrag: allDayProps.eventDrag, eventResize: allDayProps.eventResize, 
                      // timed content
                      fgEventSegsByCol: fgEventSegsByCol, bgEventSegsByCol: bgEventSegsByCol, businessHourSegsByCol: businessHourSegsByCol, nowIndicatorSegsByCol: nowIndicatorSegsByCol, dateSelectionSegsByCol: dateSelectionSegsByCol, eventDragByCol: eventDragByCol, eventResizeByCol: eventResizeByCol, 
                      // universal content
                      eventSelection: props.eventSelection }));
              } }));
      }
  }

  var timeGridPlugin = {
      name: 'timegrid',
      initialView: 'timeGridWeek',
      deps: [dayGridPlugin],
      views: {
          timeGrid: {
              component: TimeGridView,
              usesMinMaxTime: true, // indicates that slotMinTime/slotMaxTime affects rendering
              allDaySlot: true,
              slotDuration: '00:30:00',
              slotEventOverlap: true, // a bad name. confused with overlap/constraint system
          },
          timeGridDay: {
              type: 'timeGrid',
              duration: { days: 1 },
          },
          timeGridWeek: {
              type: 'timeGrid',
              duration: { weeks: 1 },
          },
      },
  };

  var timegrid = /*#__PURE__*/Object.freeze({
      __proto__: null,
      'default': timeGridPlugin
  });

  class ListDayHeaderInner extends BaseComponent {
      render() {
          const { props, context } = this;
          const { options } = context;
          const textParts = context.dateEnv.formatToParts(props.dayDate, props.dayFormat);
          const text = joinDateTimeFormatParts(textParts);
          const hasNavLink = options.navLinks;
          const renderProps = {
              ...props.dateMeta,
              view: context.viewApi,
              text,
              textParts,
              get weekdayText() { return findWeekdayText(textParts); },
              get dayNumberText() { return findDayNumberText(textParts); },
              hasNavLink,
              level: props.level,
          };
          const navLinkAttrs = hasNavLink
              ? buildNavLinkAttrs(this.context, props.dayDate, undefined, text, this.props.isTabbable)
              : {};
          return (u$1(ContentContainer, { tag: "div", attrs: navLinkAttrs, renderProps: renderProps, generatorName: "listDayHeaderContent", customGenerator: options.listDayHeaderContent, defaultGenerator: renderText$1, classNameGenerator: options.listDayHeaderInnerClass }));
      }
  }

  class ListDayHeader extends BaseComponent {
      render() {
          let { options, viewApi, viewSpec } = this.context;
          let { dayDate, dateMeta } = this.props;
          let stickyHeaderDates = !this.props.forPrint;
          const listDayFormat = options.listDayFormat ?? createDefaultListDayFormat(viewSpec);
          const listDayAltFormat = options.listDayAltFormat ?? createDefaultListDaySideFormat(viewSpec);
          let renderProps = {
              ...dateMeta,
              view: viewApi,
          };
          return (u$1(ContentContainer, { tag: "div", attrs: {
                  'data-date': formatDayString(dayDate),
                  ...(dateMeta.isToday ? { 'aria-current': 'date' } : {}),
              }, className: stickyHeaderDates ? classNames.stickyT : '', renderProps: renderProps, generatorName: undefined, classNameGenerator: options.listDayHeaderClass, didMount: options.listDayHeaderDidMount, willUnmount: options.listDayHeaderWillUnmount, children: () => (u$1(S, { children: [Boolean(listDayFormat) && (u$1(ListDayHeaderInner, { dayDate: dayDate, dayFormat: listDayFormat, isTabbable: true, dateMeta: dateMeta, level: 0 })), Boolean(listDayAltFormat) && (u$1(ListDayHeaderInner, { dayDate: dayDate, dayFormat: listDayAltFormat, isTabbable: false, dateMeta: dateMeta, level: 1 }))] })) }));
      }
  }
  function createDefaultListDayFormat({ durationUnit, singleUnit }) {
      if (singleUnit === 'day') {
          return WEEKDAY_ONLY_FORMAT;
      }
      else if (durationUnit === 'day' || singleUnit === 'week') {
          return WEEKDAY_ONLY_FORMAT;
      }
      else {
          return FULL_DATE_FORMAT;
      }
  }
  function createDefaultListDaySideFormat({ durationUnit, singleUnit }) {
      if (singleUnit === 'day') ;
      else if (durationUnit === 'day' || singleUnit === 'week') {
          return FULL_DATE_FORMAT;
      }
      else {
          return WEEKDAY_ONLY_FORMAT;
      }
  }

  const DEFAULT_TIME_FORMAT = createFormatter({
      hour: 'numeric',
      minute: '2-digit',
      meridiem: 'short',
  });
  class ListEvent extends BaseComponent {
      render() {
          let { props, context } = this;
          let { eventRange } = props;
          const { displayEventTime } = context.options;
          let forcedTimeText = (displayEventTime !== false) && (eventRange.def.allDay || (!props.isStart && !props.isEnd))
              ? context.options.allDayText
              : undefined;
          return (u$1(StandardEvent, { ...props, attrs: {
                  role: 'listitem',
              }, forcedTimeText: forcedTimeText, defaultTimeFormat: DEFAULT_TIME_FORMAT, disableDragging: true, disableResizing: true, disableZindexes // because conflicts with sticky list headers
              : true, display: 'list-item' }));
      }
  }

  class ListDay extends BaseComponent {
      constructor() {
          super(...arguments);
          // memo
          this.getDateMeta = memoize(getDateMeta);
          this.sortEventSegs = memoize(sortEventSegs);
      }
      render() {
          const { props, context } = this;
          const { nowDate, todayRange } = props;
          const { options } = context;
          const dateMeta = this.getDateMeta(props.dayDate, context.dateEnv, undefined, todayRange);
          const segs = this.sortEventSegs(props.segs, options.eventOrder);
          const fullDateStr = buildDateStr(this.context, props.dayDate);
          const listDayData = {
              ...dateMeta,
              isFirst: props.isFirst,
              isLast: props.isLast,
              view: context.viewApi,
          };
          const listDayEventsData = {
              ...dateMeta,
              view: context.viewApi,
          };
          return (u$1("div", { role: 'listitem', "aria-label": fullDateStr, className: generateClassName(options.listDayClass, listDayData), children: [u$1(ListDayHeader, { dayDate: props.dayDate, dateMeta: dateMeta, forPrint: props.forPrint }), u$1("div", { role: 'list', "aria-label": options.eventsHint, className: joinClassNames(generateClassName(options.listDayBodyClass, listDayEventsData), classNames.flexCol), children: segs.map((seg, index) => {
                          const key = seg.eventRange.instance.instanceId;
                          const isFirst = index === 0;
                          const isLast = index === segs.length - 1;
                          return (u$1(ListEvent, { eventRange: seg.eventRange, slicedStart: seg.slicedStart, slicedEnd: seg.slicedEnd, isStart: seg.isStart, isEnd: seg.isEnd, isFirst: isFirst, isLast: isLast, isDragging: false, isResizing: false, isMirror: false, isSelected: false, ...getEventRangeMeta(seg.eventRange, todayRange, nowDate, props.nowMs) }, key));
                      }) })] }));
      }
  }

  /*
  Responsible for the scroller, and forwarding event-related actions into the "grid".
  */
  class ListView extends DateComponent {
      constructor() {
          super(...arguments);
          // memo
          this.computeDateVars = memoize(computeDateVars);
          this.eventStoreToSegs = memoize(this._eventStoreToSegs);
          this.setRootEl = (rootEl) => {
              if (rootEl) {
                  this.context.registerInteractiveComponent(this, {
                      el: rootEl,
                      disableHits: true, // HACK to not do date-clicking/selecting
                  });
              }
              else {
                  this.context.unregisterInteractiveComponent(this);
              }
          };
      }
      render() {
          let { props, context } = this;
          let { options } = context;
          let { dayDates, dayRanges } = this.computeDateVars(props.dateProfile);
          let eventSegs = this.eventStoreToSegs(props.eventStore, props.eventUiBases, dayRanges);
          let verticalScrolling = !props.forPrint && !getIsHeightAuto(options);
          return (u$1(ViewContainer, { viewSpec: context.viewSpec, className: joinClassNames(props.className, classNames.flexCol), elRef: this.setRootEl, children: eventSegs.length ? (u$1(Scroller // TODO: don't need heavyweight component
              , { vertical: verticalScrolling, className: joinClassNames(classNames.flexCol, verticalScrolling ? classNames.liquid : ''), children: this.renderSegList(eventSegs, dayDates) })) : this.renderEmptyMessage() }));
      }
      renderEmptyMessage() {
          let { options, viewApi } = this.context;
          let renderProps = {
              text: options.noEventsText,
              view: viewApi,
          };
          return (u$1(ContentContainer, { tag: "div", attrs: {
                  role: 'status', // does a polite announcement
              }, renderProps: renderProps, generatorName: "noEventsContent", customGenerator: options.noEventsContent, defaultGenerator: renderNoEventsInner, classNameGenerator: options.noEventsClass, className: classNames.grow, didMount: options.noEventsDidMount, willUnmount: options.noEventsWillUnmount, children: (InnerContent) => (u$1(InnerContent, { tag: "div", className: generateClassName(options.noEventsInnerClass, renderProps) })) }));
      }
      renderSegList(allSegs, dayDates) {
          let { options } = this.context;
          let segsByDay = groupSegsByDay(allSegs); // sparse array
          return (u$1("div", { role: "list", "aria-labelledby": this.props.labelId, "aria-label": this.props.labelStr, className: joinClassNames(classNames.flexCol, joinClassNames(options.listDaysClass)), children: u$1(NowTimer, { unit: "day", children: (nowDate, todayRange, nowMs) => {
                      const dayNodes = [];
                      const populatedDayCount = segsByDay.reduce((count, daySegs) => count + (daySegs ? 1 : 0), 0);
                      let populatedDayIndex = 0;
                      for (let dayIndex = 0; dayIndex < segsByDay.length; dayIndex += 1) {
                          let daySegs = segsByDay[dayIndex];
                          if (daySegs) { // sparse array, so might be undefined
                              const dayDate = dayDates[dayIndex];
                              const key = formatDayString(dayDate);
                              const isFirst = populatedDayIndex === 0;
                              const isLast = populatedDayIndex === populatedDayCount - 1;
                              dayNodes.push(u$1(ListDay, { dayDate: dayDate, nowDate: nowDate, nowMs: nowMs, todayRange: todayRange, segs: daySegs, isFirst: isFirst, isLast: isLast, forPrint: this.props.forPrint }, key));
                              populatedDayIndex += 1;
                          }
                      }
                      return (u$1(S, { children: dayNodes }));
                  } }) }));
      }
      _eventStoreToSegs(eventStore, eventUiBases, dayRanges) {
          return this.eventRangesToSegs(sliceEventStore(eventStore, eventUiBases, 
          // HACKY to reference internal state...
          this.props.dateProfile.activeRange, this.context.options.nextDayThreshold).fg, dayRanges);
      }
      eventRangesToSegs(fullDayEventRanges, dayRanges) {
          let segs = [];
          for (let fullDayEventRange of fullDayEventRanges) {
              segs.push(...this.eventRangeToSegs(fullDayEventRange, dayRanges));
          }
          return segs;
      }
      eventRangeToSegs(fullDayEventRange, dayRanges) {
          let fullDayRange = fullDayEventRange.range;
          let dayIndex;
          let segs = [];
          for (dayIndex = 0; dayIndex < dayRanges.length; dayIndex += 1) {
              const slicedFullDayRange = intersectRanges(fullDayRange, dayRanges[dayIndex]);
              if (slicedFullDayRange) {
                  segs.push({
                      eventRange: fullDayEventRange,
                      slicedStart: slicedFullDayRange.start,
                      slicedEnd: slicedFullDayRange.end,
                      isStart: fullDayEventRange.isStart && fullDayRange.start.valueOf() === slicedFullDayRange.start.valueOf(),
                      isEnd: fullDayEventRange.isEnd && fullDayRange.end.valueOf() === slicedFullDayRange.end.valueOf(),
                      dayIndex,
                  });
              }
          }
          return segs;
      }
  }
  function renderNoEventsInner(renderProps) {
      return renderProps.text;
  }
  function computeDateVars(dateProfile) {
      let dayStart = startOfDay(dateProfile.renderRange.start);
      let viewEnd = dateProfile.renderRange.end;
      let dayDates = [];
      let dayRanges = [];
      while (dayStart < viewEnd) {
          dayDates.push(dayStart);
          dayRanges.push({
              start: dayStart,
              end: addDays(dayStart, 1),
          });
          dayStart = addDays(dayStart, 1);
      }
      return { dayDates, dayRanges };
  }
  // Returns a sparse array of arrays, segs grouped by their dayIndex
  function groupSegsByDay(segs) {
      let segsByDay = []; // sparse array
      let i;
      let seg;
      for (i = 0; i < segs.length; i += 1) {
          seg = segs[i];
          (segsByDay[seg.dayIndex] || (segsByDay[seg.dayIndex] = []))
              .push(seg);
      }
      return segsByDay;
  }

  var listPlugin = {
      name: 'list',
      views: {
          list: {
              component: ListView,
              buttonTextKey: 'listText', // what to lookup in locale files
              disallowAmbigTitle: true,
          },
          listDay: {
              type: 'list',
              duration: { days: 1 },
          },
          listWeek: {
              type: 'list',
              duration: { weeks: 1 },
          },
          listMonth: {
              type: 'list',
              duration: { month: 1 },
          },
          listYear: {
              type: 'list',
              duration: { year: 1 },
          },
      },
  };

  var list = /*#__PURE__*/Object.freeze({
      __proto__: null,
      'default': listPlugin
  });

  class SingleMonth extends DateComponent {
      constructor() {
          super(...arguments);
          this.state = {};
          // memo
          this.buildDayTableModel = memoize(buildDayTableModel);
          this.createDayHeaderFormatter = memoize(createDayHeaderFormatter);
          this.buildDateRowConfig = memoize(buildDateRowConfig);
          // ref
          this.titleElRef = M$1();
          this.rowHeightRefMap = new RefMap(() => {
              afterSize(this.handleHeights);
          });
          this.slicer = new DayTableSlicer();
          this.handleEl = (el) => {
              const { options } = this.context;
              if (el) {
                  this.rootEl = el;
                  options.singleMonthDidMount?.({
                      el: this.rootEl,
                      ...this.renderProps,
                  });
              }
          };
          this.handleTableHeaderEl = (el) => {
              this.disconnectTableHeaderHeight?.();
              this.disconnectTableHeaderHeight = undefined;
              if (el) {
                  this.disconnectTableHeaderHeight = watchHeight(el, (height) => {
                      this.setState({ tableHeaderHeight: this.tableHeaderHeight = height });
                      afterSize(this.handleHeights);
                  });
              }
          };
          this.handleGridWidth = (gridWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ gridWidth });
          };
          this.handleHeights = () => {
              if (this._isUnmounting)
                  return;
              setRef(this.props.heightsRef, {
                  titleHeight: this.titleHeight,
                  tableHeaderHeight: this.tableHeaderHeight,
                  rowHeightMap: this.rowHeightRefMap.current,
                  cellRows: this.cellRows,
              });
          };
      }
      get titleId() {
          return this.context.baseId + 'month-' + this.props.isoDateStr;
      }
      render() {
          const { props, state, context } = this;
          const { dateProfile, forPrint } = props;
          const { options, dateEnv } = context;
          const { borderlessX, borderlessTop, borderlessBottom } = computeViewBorderless(options);
          const dayTableModel = this.buildDayTableModel(dateProfile, context.dateProfileGenerator, dateEnv);
          const slicedProps = this.slicer.sliceProps(props, dateProfile, options.nextDayThreshold, context, dayTableModel);
          const dayHeaderFormat = this.createDayHeaderFormatter(options.dayHeaderFormat, false, // datesRepDistinctDays
          dayTableModel.colCount);
          const rowConfig = this.buildDateRowConfig(dayTableModel.headerDates, false, // datesRepDistinctDays
          dateProfile, props.todayRange, dayHeaderFormat, context);
          this.cellRows = dayTableModel.cellRows;
          const isTitleAndHeaderSticky = !forPrint && props.colCount === 1;
          const isAspectRatio = !forPrint || props.hasLateralSiblings;
          const cellColCnt = dayTableModel.cellRows[0].length;
          const measuredColWidth = state.gridWidth != null ? state.gridWidth / cellColCnt : undefined;
          const cellIsMicro = measuredColWidth != null && measuredColWidth <= dayMicroWidth;
          const cellIsNarrow = cellIsMicro || (measuredColWidth != null && measuredColWidth <= options.dayNarrowWidth);
          const rowHeightGuess = state.gridWidth != null
              ? (1 / options.aspectRatio) * state.gridWidth / 6
              : undefined;
          const headerStickyBottom = isTitleAndHeaderSticky
              ? rowHeightGuess
              : undefined;
          const titleStickyBottom = isTitleAndHeaderSticky && rowHeightGuess != null && state.tableHeaderHeight != null
              ? rowHeightGuess + state.tableHeaderHeight + 1
              : undefined;
          const businessHourSegs = slicedProps.businessHourSegs;
          const dateSelectionSegs = forPrint ? [] : slicedProps.dateSelectionSegs;
          const eventDrag = forPrint ? null : slicedProps.eventDrag;
          const eventResize = forPrint ? null : slicedProps.eventResize;
          const tableMode = forPrint && !props.hasLateralSiblings;
          const hasNavLink = options.navLinks && props.colCount > 1;
          const headerRenderProps = {
              multiMonthColumns: props.colCount || 0,
              isSticky: isTitleAndHeaderSticky,
              isNarrow: cellIsNarrow,
              hasNavLink,
          };
          const monthStartDate = props.dateProfile.currentRange.start;
          const navLinkAttrs = hasNavLink
              ? buildNavLinkAttrs(context, monthStartDate, 'month', props.isoDateStr)
              : {};
          return (u$1("div", { role: 'listitem', style: { width: props.width }, children: u$1("div", { role: 'grid', "aria-labelledby": this.titleId, "data-date": props.isoDateStr, className: joinClassNames(generateClassName(options.singleMonthClass, {
                      isFirst: props.isFirst,
                      isLast: props.isLast,
                      multiMonthColumns: props.colCount || 0,
                  }), classNames.flexCol, props.hasLateralSiblings && classNames.breakInsideAvoid), children: [u$1(Ruler, { widthRef: this.handleGridWidth }), u$1("div", { id: this.titleId, ref: this.titleElRef, className: joinClassNames(generateClassName(options.singleMonthHeaderClass, headerRenderProps), isTitleAndHeaderSticky && classNames.stickyT, isTitleAndHeaderSticky && classNames.z3, classNames.flexCol), style: {
                              // HACK to keep zIndex above table-header,
                              // because in Chrome, something about position:sticky on this title div
                              // causes its bottom border to no be considered part of its mass,
                              // and would get overlapped and hidden by the table-header div
                              marginBottom: titleStickyBottom,
                          }, children: u$1("div", { ...navLinkAttrs, className: joinClassNames(generateClassName(options.singleMonthHeaderInnerClass, headerRenderProps), navLinkAttrs.className), children: joinDateTimeFormatParts(dateEnv.formatToParts(monthStartDate, props.titleFormat)) }) }), tableMode ? (u$1(DayGridLayoutPrint, { dateProfile: props.dateProfile, todayRange: props.todayRange, cellRows: dayTableModel.cellRows, headerTiers: [rowConfig], showHeader: true, headerElRef: this.handleTableHeaderEl, fgEventSegs: slicedProps.fgEventSegs, bgEventSegs: slicedProps.bgEventSegs, businessHourSegs: businessHourSegs, eventSelection: slicedProps.eventSelection, dayMaxEventRows: true, borderlessX: borderlessX, borderlessTop: borderlessTop, borderlessBottom: borderlessBottom, multiMonthColumns: props.colCount || 0, visibleWidth: state.gridWidth, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, rowHeightRefMap: this.rowHeightRefMap, style: {
                              marginTop: titleStickyBottom != null ? -titleStickyBottom : undefined,
                          } })) : (u$1("div", { className: joinClassNames(generateClassName(options.tableClass, {
                              borderlessX,
                              borderlessTop,
                              borderlessBottom,
                              multiMonthColumns: props.colCount || 0,
                          }), classNames.flexCol), style: {
                              marginTop: titleStickyBottom != null ? -titleStickyBottom : undefined,
                          }, children: [u$1("div", { ref: this.handleTableHeaderEl, className: joinClassNames(generateClassName(options.tableHeaderClass, {
                                      isSticky: isTitleAndHeaderSticky,
                                      borderlessX,
                                      borderlessTop,
                                      borderlessBottom,
                                      multiMonthColumns: props.colCount || 0,
                                  }), classNames.flexCol, isTitleAndHeaderSticky && classNames.sticky, isTitleAndHeaderSticky && classNames.z2), style: {
                                      top: isTitleAndHeaderSticky ? state.titleHeight : 0,
                                      marginBottom: headerStickyBottom,
                                  }, children: [u$1(DayGridHeaderRow, { ...rowConfig, role: 'row', borderBottom: false, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, rowLevel: 0 }), u$1("div", { className: generateClassName(options.dayHeaderDividerClass, {
                                              isSticky: isTitleAndHeaderSticky,
                                              multiMonthColumns: props.colCount || 0,
                                              options: { allDaySlot: Boolean(options.allDaySlot) },
                                          }) })] }), u$1("div", { className: joinClassNames(generateClassName(options.tableBodyClass, {
                                      borderlessX,
                                      borderlessTop,
                                      borderlessBottom,
                                      multiMonthColumns: props.colCount || 0,
                                  }), classNames.flexCol, isAspectRatio && classNames.rel, isTitleAndHeaderSticky && classNames.z1), style: {
                                      marginTop: headerStickyBottom != null ? -headerStickyBottom : undefined,
                                      aspectRatio: isAspectRatio ? String(options.aspectRatio) : undefined,
                                  }, children: u$1(DayGridRows, { dateProfile: props.dateProfile, todayRange: props.todayRange, cellRows: dayTableModel.cellRows, className: isAspectRatio ? classNames.fill : '', forPrint: forPrint && !props.hasLateralSiblings, dayMaxEventRows: (forPrint && props.hasLateralSiblings)
                                          ? 1 // for side-by-side multimonths, limit to one row
                                          : true // otherwise, always do +more link, never expand rows
                                      , 
                                      // content
                                      fgEventSegs: slicedProps.fgEventSegs, bgEventSegs: slicedProps.bgEventSegs, businessHourSegs: businessHourSegs, dateSelectionSegs: dateSelectionSegs, eventDrag: eventDrag, eventResize: eventResize, eventSelection: slicedProps.eventSelection, 
                                      // dimensions
                                      visibleWidth: state.gridWidth, cellIsNarrow: cellIsNarrow, cellIsMicro: cellIsMicro, rowHeightRefMap: this.rowHeightRefMap }) })] }))] }) }));
      }
      componentDidMount() {
          this._isUnmounting = false;
          this.disconnectTitleHeight = watchHeight(this.titleElRef.current, (height) => {
              this.setState({ titleHeight: this.titleHeight = height });
              afterSize(this.handleHeights);
          });
      }
      componentWillUnmount() {
          const { options } = this.context;
          this._isUnmounting = true;
          this.disconnectTitleHeight();
          this.disconnectTableHeaderHeight?.();
          options.singleMonthWillUnmount?.({
              el: this.rootEl,
              ...this.renderProps,
          });
      }
  }

  class MultiMonthView extends DateComponent {
      constructor() {
          super(...arguments);
          this.state = {};
          // memo
          this.splitDateProfileByMonth = memoize(splitDateProfileByMonth);
          this.buildMonthFormat = memoize(buildMonthFormat);
          // ref
          this.scrollerRef = M$1();
          this.tilesElRef = M$1();
          this.scrollState = {};
          // Scrolling
          // -----------------------------------------------------------------------------------------------
          this.handleInnerWidth = (innerWidth) => {
              if (this._isUnmounting)
                  return;
              this.setState({ innerWidth });
          };
          this.handleScrollStart = () => {
              this.scrollState.date = undefined;
              this.scrollState.top = undefined;
          };
          this.handleScrollEnd = (isDevice) => {
              const scroller = this.scrollerRef.current;
              if (isDevice && scroller) {
                  this.scrollState.top = scroller.y;
                  this.scrollState.date = undefined;
              }
          };
      }
      render() {
          const { context, props, state } = this;
          const { options } = context;
          const verticalScrolling = !props.forPrint && !getIsHeightAuto(options);
          const monthDateProfiles = this.splitDateProfileByMonth(context.dateProfileGenerator, props.dateProfile, context.dateEnv, options.fixedWeekCount, options.showNonCurrentDates);
          const monthTitleFormat = this.buildMonthFormat(options.singleMonthTitleFormat, monthDateProfiles);
          const { multiMonthMaxColumns, singleMonthMinWidth } = options;
          const { innerWidth } = state;
          let cols;
          let cssMonthWidth;
          let hasLateralSiblings = false;
          if (innerWidth != null) {
              cols = Math.max(1, Math.min(multiMonthMaxColumns, Math.floor(innerWidth / singleMonthMinWidth)));
              if (props.forPrint) {
                  cols = Math.min(cols, 2);
              }
              cssMonthWidth = fracToCssDim(1 / cols);
              hasLateralSiblings = cols > 1;
          }
          return (u$1(NowTimer, { unit: "day", children: (nowDate, todayRange) => (u$1(ViewContainer, { viewSpec: context.viewSpec, className: joinClassNames(
                  // HACK for Safari. Can't do break-inside:avoid with flexbox items, likely b/c it's not standard:
                  // https://stackoverflow.com/a/60256345
                  !props.forPrint && classNames.flexCol, props.className), children: [u$1(Scroller, { vertical: verticalScrolling, className: verticalScrolling ? classNames.liquid : '', ref: this.scrollerRef, children: u$1("div", { role: 'list', ref: this.tilesElRef, "aria-labelledby": props.labelId, "aria-label": props.labelStr, className: classNames.safeTiles, children: monthDateProfiles.map((monthDateProfile, i) => {
                                  const monthStr = formatIsoMonthStr(monthDateProfile.currentRange.start);
                                  return (k$1(SingleMonth, { ...props, key: monthStr, todayRange: todayRange, isoDateStr: monthStr, titleFormat: monthTitleFormat, dateProfile: monthDateProfile, width: cssMonthWidth, colCount: cols, isFirst: !i, isLast: i === monthDateProfiles.length - 1, hasLateralSiblings: hasLateralSiblings }));
                              }) }) }), u$1(Ruler, { widthRef: this.handleInnerWidth })] })) }));
      }
      // Lifecycle
      // -----------------------------------------------------------------------------------------------
      componentDidMount() {
          this._isUnmounting = false;
          this.scrollState.date = this.props.dateProfile.currentDate;
          this.scrollerRef.current.addScrollStartListener(this.handleScrollStart);
          this.scrollerRef.current.addScrollEndListener(this.handleScrollEnd);
          // this.applyScroll() // definitely not ready yet b/c doesn't have state.innerWidth
          // workaround for off-by-a-few-pixels on first time when multiMonthMaxColumns=1, not sure why
          setTimeout(() => {
              this.applyScroll();
          }, 0);
      }
      componentDidUpdate(prevProps, prevState) {
          if (prevProps.dateProfile !== this.props.dateProfile) {
              if (this.context.options.scrollTimeReset) {
                  this.resetScroll();
              }
              else {
                  this.applyScroll();
              }
          }
          else if (prevState.innerWidth !== this.state.innerWidth) {
              this.applyScroll();
          }
      }
      componentWillUnmount() {
          this._isUnmounting = true;
          this.scrollerRef.current.removeScrollStartListener(this.handleScrollStart);
          this.scrollerRef.current.removeScrollEndListener(this.handleScrollEnd);
      }
      resetScroll() {
          this.scrollState.date = this.props.dateProfile.currentDate;
          this.scrollState.top = undefined;
          this.applyScroll();
      }
      applyScroll() {
          const scroller = this.scrollerRef.current;
          const top = this.computeScrollTop();
          if (scroller && top != null) {
              scroller.scrollTo({ y: top });
          }
      }
      computeScrollTop() {
          const { scrollState } = this;
          if (scrollState.top != null) {
              return scrollState.top;
          }
          if (scrollState.date != null) {
              const tilesEl = this.tilesElRef.current;
              const monthEl = tilesEl?.querySelector(`[data-date="${formatIsoMonthStr(scrollState.date)}"]`);
              const monthWrapEl = monthEl?.parentElement;
              if (tilesEl && monthWrapEl) {
                  // rounding required for proper alignment
                  const monthTop = Math.round(monthWrapEl.getBoundingClientRect().top);
                  const originTop = Math.round(tilesEl.getBoundingClientRect().top);
                  return monthTop - originTop;
              }
          }
      }
  }
  // date profile
  // -------------------------------------------------------------------------------------------------
  const oneMonthDuration = createDuration(1, 'month');
  function splitDateProfileByMonth(dateProfileGenerator, dateProfile, dateEnv, fixedWeekCount, showNonCurrentDates) {
      const { start, end } = dateProfile.currentRange;
      let monthStart = start;
      const monthDateProfiles = [];
      while (monthStart.valueOf() < end.valueOf()) {
          const monthEnd = dateEnv.add(monthStart, oneMonthDuration);
          const currentRange = {
              // yuck
              start: dateProfileGenerator.skipHiddenDays(monthStart),
              end: dateProfileGenerator.skipHiddenDays(monthEnd, -1, true),
          };
          let renderRange = buildDayTableRenderRange({
              currentRange,
              snapToWeek: true,
              fixedWeekCount,
              dateEnv,
          });
          renderRange = {
              // yuck
              start: dateProfileGenerator.skipHiddenDays(renderRange.start),
              end: dateProfileGenerator.skipHiddenDays(renderRange.end, -1, true),
          };
          const activeRange = dateProfile.activeRange ?
              intersectRanges(dateProfile.activeRange, showNonCurrentDates ? renderRange : currentRange) :
              null;
          monthDateProfiles.push({
              currentDate: dateProfile.currentDate,
              isValid: dateProfile.isValid,
              validRange: dateProfile.validRange,
              renderRange,
              activeRange,
              currentRange,
              currentRangeUnit: 'month',
              isRangeAllDay: true,
              dateIncrement: dateProfile.dateIncrement,
              slotMinTime: dateProfile.slotMaxTime,
              slotMaxTime: dateProfile.slotMinTime,
          });
          monthStart = monthEnd;
      }
      return monthDateProfiles;
  }
  // date formatting
  // -------------------------------------------------------------------------------------------------
  const YEAR_MONTH_FORMATTER = createFormatter({ year: 'numeric', month: 'long' });
  const YEAR_FORMATTER = createFormatter({ month: 'long' });
  function buildMonthFormat(formatOverride, monthDateProfiles) {
      return formatOverride ||
          ((monthDateProfiles[0].currentRange.start.getUTCFullYear() !==
              monthDateProfiles[monthDateProfiles.length - 1].currentRange.start.getUTCFullYear())
              ? YEAR_MONTH_FORMATTER
              : YEAR_FORMATTER);
  }

  var multiMonthPlugin = {
      name: 'multimonth',
      initialView: 'multiMonthYear',
      views: {
          multiMonth: {
              component: MultiMonthView,
              dateProfileGeneratorClass: TableDateProfileGenerator,
              multiMonthMaxColumns: 3,
              singleMonthMinWidth: 350,
          },
          multiMonthYear: {
              type: 'multiMonth',
              duration: { years: 1 },
              fixedWeekCount: true, // TODO: apply to all multi-col layouts?
              showNonCurrentDates: false, // TODO: looks bad when single-col layout
          },
      },
  };

  var multimonth = /*#__PURE__*/Object.freeze({
      __proto__: null,
      'default': multiMonthPlugin
  });

  const blankButtonState = {
      text: '', hint: '', isDisabled: false,
  };
  class CalendarController {
      constructor(handleDateChange) {
          this.handleDateChange = handleDateChange;
      }
      today() {
          this.calendarApi?.today();
      }
      prev() {
          this.calendarApi?.prev();
      }
      next() {
          this.calendarApi?.next();
      }
      prevYear() {
          this.calendarApi?.prevYear();
      }
      nextYear() {
          this.calendarApi?.nextYear();
      }
      gotoDate(zonedDateInput) {
          this.calendarApi?.gotoDate(zonedDateInput);
      }
      incrementDate(duration) {
          this.calendarApi?.incrementDate(duration);
      }
      changeView(viewType) {
          this.calendarApi?.changeView(viewType);
      }
      get view() {
          return this.calendarApi?.view;
      }
      getDate() {
          return this.calendarApi?.getDate();
      }
      getButtonState() {
          const { calendarApi } = this;
          return (calendarApi && calendarApi.getButtonState()) || {
              today: blankButtonState,
              prev: blankButtonState,
              next: blankButtonState,
              prevYear: blankButtonState,
              nextYear: blankButtonState,
          };
      }
      _setApi(calendarApi) {
          if (this.calendarApi !== calendarApi) {
              if (this.calendarApi) {
                  this.calendarApi.off('datesSet', this.handleDateChange);
                  this.calendarApi = undefined;
              }
              if (calendarApi) {
                  this.calendarApi = calendarApi;
                  calendarApi.on('datesSet', this.handleDateChange);
              }
          }
      }
  }

  function formatDate(dateInput, options = {}) {
      let dateEnv = buildDateEnv(options);
      let formatter = createFormatter(options);
      let dateMeta = dateEnv.createMarkerMeta(dateInput);
      if (!dateMeta) { // TODO: warning?
          return '';
      }
      return joinDateTimeFormatParts(dateEnv.formatToParts(dateMeta.marker, formatter, {
          instantMs: dateMeta.instantMs,
      }));
  }
  function formatRange(startInput, endInput, options) {
      let dateEnv = buildDateEnv(typeof options === 'object' && options ? options : {}); // pass in if non-null object
      let formatter = createFormatter(options);
      let startMeta = dateEnv.createMarkerMeta(startInput);
      let endMeta = dateEnv.createMarkerMeta(endInput);
      if (!startMeta || !endMeta) { // TODO: warning?
          return '';
      }
      return joinDateTimeFormatParts(dateEnv.formatRangeToParts(startMeta.marker, endMeta.marker, formatter, {
          isEndExclusive: options.isEndExclusive,
          startInstantMs: startMeta.instantMs,
          endInstantMs: endMeta.instantMs,
      }));
  }
  // TODO: more DRY and optimized
  function buildDateEnv(settings) {
      let locale = buildLocale(settings.locale || 'en', organizeRawLocales([]).map); // TODO: don't hardcode 'en' everywhere
      return new DateEnv({
          timeZone: BASE_OPTION_DEFAULTS.timeZone,
          calendarSystem: 'gregory',
          ...settings,
          locale,
      });
  }

  /*
  if nextDayThreshold is specified, slicing is done in an all-day fashion.
  you can get nextDayThreshold from context.nextDayThreshold
  */
  function sliceEvents(props, allDay) {
      return sliceEventStore(props.eventStore, props.eventUiBases, props.dateProfile.activeRange, allDay ? props.nextDayThreshold : null).fg;
  }

  const version = '7.1.0';

  var protectedStyles = /*#__PURE__*/Object.freeze({
  	__proto__: null,
  	'default': classNames
  });

  function createRoot(container) {
  	return {
  		// eslint-disable-next-line
  		render: function (children) {
  			nn(children, container);
  		},
  		// eslint-disable-next-line
  		unmount: function () {
  			pn(container);
  		}
  	};
  }

  /*
  Vanilla JS API
  */
  class Calendar$1 extends CalendarApiImpl {
      constructor(el, optionOverrides = {}) {
          super();
          this.baseId = `fc:${guid()}:`;
          this.isRendering = false;
          this.isRendered = false;
          this.customContentRenderId = 0;
          this.currentClassName = '';
          this.currentColorScheme = '';
          this.handleDataChange = (data, actions) => {
              this.currentData = data;
              let renderImmediate = false;
              for (const action of actions) {
                  if (action.type === 'SET_EVENT_DRAG' ||
                      action.type === 'UNSET_EVENT_DRAG' ||
                      action.type === 'SET_EVENT_RESIZE' ||
                      action.type === 'UNSET_EVENT_RESIZE' ||
                      // could happen as a result of a drag or resize and must be part of same sync pipeline
                      action.type === 'MERGE_EVENTS') {
                      renderImmediate = true;
                      break;
                  }
              }
              this.renderRunner.request(renderImmediate ? undefined : data.calendarOptions.rerenderDelay);
          };
          this.handleRenderRequest = () => {
              if (this.isRendering) {
                  let { currentData } = this;
                  this.isRendered = true;
                  bn(() => {
                      this.vdomRoot.render(u$1(S, { children: u$1(RenderId.Provider, { value: this.customContentRenderId, children: u$1(CalendarMediaRoot, { emitter: currentData.emitter, children: (forPrint) => {
                                      const options = currentData.calendarOptions;
                                      const isRtl = options.direction === 'rtl';
                                      const className = computeRootClassName(options, forPrint);
                                      this.setIsRtl(isRtl);
                                      this.setClassName(className);
                                      this.setHeight(options.height);
                                      this.setColorScheme(options.colorScheme || '');
                                      return (u$1(CalendarInner, { ...currentData, forPrint: forPrint, baseId: this.baseId }));
                                  } }) }) }));
                  });
              }
              else if (this.isRendered) {
                  this.isRendered = false;
                  this.vdomRoot.unmount();
                  this.setIsRtl(false);
                  this.setClassName('');
                  this.setHeight('');
                  this.setColorScheme('');
              }
          };
          this.el = el;
          this.vdomRoot = createRoot(el);
          this.renderRunner = new DelayedRunner(this.handleRenderRequest);
          this.dataManager = new CalendarDataManager({
              calendarApi: this,
              onDataChange: this.handleDataChange,
          });
          this.currentData = this.dataManager.update(optionOverrides);
      }
      render() {
          let wasRendering = this.isRendering;
          if (!wasRendering) {
              this.isRendering = true;
          }
          else {
              this.customContentRenderId += 1;
          }
          this.renderRunner.request();
      }
      destroy() {
          if (this.isRendering) {
              this.isRendering = false;
              this.renderRunner.request();
          }
          this.dataManager.destroy();
      }
      batchRendering(func) {
          this.renderRunner.pause('batchRendering');
          func();
          this.renderRunner.resume('batchRendering');
      }
      pauseRendering() {
          this.renderRunner.pause('pauseRendering');
      }
      resumeRendering() {
          this.renderRunner.resume('pauseRendering', true);
      }
      resetOptions(optionOverrides, changedOptionNames) {
          this.currentDataManager.resetOptions(optionOverrides, changedOptionNames);
      }
      setClassName(className) {
          if (className !== this.currentClassName) {
              let { classList } = this.el;
              for (let singleClassName of this.currentClassName.split(' ')) {
                  if (singleClassName) {
                      classList.remove(singleClassName);
                  }
              }
              for (let singleClassName of className.split(' ')) {
                  if (singleClassName) {
                      classList.add(singleClassName);
                  }
              }
              this.currentClassName = className;
          }
      }
      setHeight(height) {
          applyStyleProp(this.el, 'height', height);
      }
      setColorScheme(colorScheme) {
          if (colorScheme !== this.currentColorScheme) {
              if (colorScheme) {
                  this.el.dataset.colorScheme = colorScheme;
              }
              else {
                  delete this.el.dataset.colorScheme;
              }
              this.currentColorScheme = colorScheme;
          }
      }
      setIsRtl(isRtl) {
          if (isRtl) {
              this.el.dir = 'rtl';
          }
          else {
              this.el.removeAttribute('dir');
          }
      }
  }

  const plugins = [
      interactionPlugin,
      dayGridPlugin,
      timeGridPlugin,
      listPlugin,
      multiMonthPlugin,
  ];
  class Calendar extends Calendar$1 {
      constructor(el, optionOverrides = {}) {
          super(el, {
              ...optionOverrides,
              plugins: [
                  ...plugins,
                  ...(optionOverrides.plugins || []),
              ]
          });
      }
  }

  const Shared = { F: globalLocales, G: globalPlugins, H: joinClassNames, S, u: u$1 };

  exports.Calendar = Calendar;
  exports.CalendarController = CalendarController;
  exports.DayGrid = daygrid;
  exports.Interaction = interaction;
  exports.JsonRequestError = JsonRequestError;
  exports.List = list;
  exports.MultiMonth = multimonth;
  exports.Preact = preact;
  exports.PreactJSXRuntime = jsxRuntime;
  exports.ProtectedApi = protectedApi;
  exports.ProtectedStyles = protectedStyles;
  exports.Shared = Shared;
  exports.TimeGrid = timegrid;
  exports.formatDate = formatDate;
  exports.formatRange = formatRange;
  exports.globalLocales = globalLocales;
  exports.globalPlugins = globalPlugins;
  exports.joinClassNames = joinClassNames;
  exports.sliceEvents = sliceEvents;
  exports.version = version;

  Object.defineProperty(exports, '__esModule', { value: true });

  return exports;

})({});
