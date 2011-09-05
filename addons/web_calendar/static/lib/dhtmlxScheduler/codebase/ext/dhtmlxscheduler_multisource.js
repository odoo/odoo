/*
This software is allowed to use under GPL or you need to obtain Commercial or Enterise License
to use it in not GPL project. Please contact sales@dhtmlx.com for details
*/
(function(){function e(a){var b=function(){};b.prototype=a;return b}var d=scheduler._load;scheduler._load=function(a,b){a=a||this._load_url;if(typeof a=="object")for(var f=e(this._loaded),c=0;c<a.length;c++)this._loaded=new f,d.call(this,a[c],b);else d.apply(this,arguments)}})();
