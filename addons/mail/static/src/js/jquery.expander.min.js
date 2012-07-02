/*!
 * jQuery Expander Plugin v1.4.2
 *
 * Date: Sat Mar 31 20:51:48 2012 EDT
 * Requires: jQuery v1.3+
 *
 * Copyright 2011, Karl Swedberg
 * Dual licensed under the MIT and GPL licenses (just like jQuery):
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
 *
 *
 *
 *
*/
(function(c){c.expander={version:"1.4.2",defaults:{slicePoint:100,preserveWords:true,widow:4,expandText:"read more",expandPrefix:"&hellip; ",expandAfterSummary:false,summaryClass:"summary",detailClass:"details",moreClass:"read-more",lessClass:"read-less",collapseTimer:0,expandEffect:"slideDown",expandSpeed:250,collapseEffect:"slideUp",collapseSpeed:200,userCollapse:true,userCollapseText:"read less",userCollapsePrefix:" ",onSlice:null,beforeExpand:null,afterExpand:null,onCollapse:null}};c.fn.expander=
function(l){function J(a,d){var g="span",h=a.summary;if(d){g="div";if(x.test(h)&&!a.expandAfterSummary)h=h.replace(x,a.moreLabel+"$1");else h+=a.moreLabel;h='<div class="'+a.summaryClass+'">'+h+"</div>"}else h+=a.moreLabel;return[h,"<",g+' class="'+a.detailClass+'"',">",a.details,"</"+g+">"].join("")}function K(a){var d='<span class="'+a.moreClass+'">'+a.expandPrefix;d+='<a href="#">'+a.expandText+"</a></span>";return d}function y(a,d){if(a.lastIndexOf("<")>a.lastIndexOf(">"))a=a.slice(0,a.lastIndexOf("<"));
if(d)a=a.replace(L,"");return c.trim(a)}function z(a,d){d.stop(true,true)[a.collapseEffect](a.collapseSpeed,function(){d.prev("span."+a.moreClass).show().length||d.parent().children("div."+a.summaryClass).show().find("span."+a.moreClass).show()})}function M(a,d,g){if(a.collapseTimer)A=setTimeout(function(){z(a,d);c.isFunction(a.onCollapse)&&a.onCollapse.call(g,false)},a.collapseTimer)}var v="init";if(typeof l=="string"){v=l;l={}}var o=c.extend({},c.expander.defaults,l),N=/^<(?:area|br|col|embed|hr|img|input|link|meta|param).*>$/i,
L=o.wordEnd||/(&(?:[^;]+;)?|[a-zA-Z\u00C0-\u0100]+)$/,B=/<\/?(\w+)[^>]*>/g,C=/<(\w+)[^>]*>/g,D=/<\/(\w+)>/g,x=/(<\/[^>]+>)\s*$/,O=/^<[^>]+>.?/,A;l={init:function(){this.each(function(){var a,d,g,h,m,i,p,w,E=[],t=[],q={},r=this,f=c(this),F=c([]),b=c.meta?c.extend({},o,f.data()):o;i=!!f.find("."+b.detailClass).length;var s=!!f.find("*").filter(function(){return/^block|table|list/.test(c(this).css("display"))}).length,u=(s?"div":"span")+"."+b.detailClass,G="span."+b.moreClass,P=b.expandSpeed||0,n=c.trim(f.html());
c.trim(f.text());var e=n.slice(0,b.slicePoint);if(!c.data(this,"expander")){c.data(this,"expander",true);c.each(["onSlice","beforeExpand","afterExpand","onCollapse"],function(j,k){q[k]=c.isFunction(b[k])});e=y(e);for(d=e.replace(B,"").length;d<b.slicePoint;){a=n.charAt(e.length);if(a=="<")a=n.slice(e.length).match(O)[0];e+=a;d++}e=y(e,b.preserveWords);h=e.match(C)||[];m=e.match(D)||[];g=[];c.each(h,function(j,k){N.test(k)||g.push(k)});h=g;d=m.length;for(a=0;a<d;a++)m[a]=m[a].replace(D,"$1");c.each(h,
function(j,k){var H=k.replace(C,"$1"),I=c.inArray(H,m);if(I===-1){E.push(k);t.push("</"+H+">")}else m.splice(I,1)});t.reverse();if(i){i=f.find(u).remove().html();e=f.html();n=e+i;a=""}else{i=n.slice(e.length);a=c.trim(i.replace(B,""));if(a===""||a.split(/\s+/).length<b.widow)return;a=t.pop()||"";e+=t.join("");i=E.join("")+i}b.moreLabel=f.find(G).length?"":K(b);if(s)i=n;e+=a;b.summary=e;b.details=i;b.lastCloseTag=a;if(q.onSlice)b=(g=b.onSlice.call(r,b))&&g.details?g:b;s=J(b,s);f.html(s);p=f.find(u);
w=f.find(G);p.hide();w.find("a").unbind("click.expander").bind("click.expander",function(j){j.preventDefault();w.hide();F.hide();q.beforeExpand&&b.beforeExpand.call(r);p.stop(false,true)[b.expandEffect](P,function(){p.css({zoom:""});q.afterExpand&&b.afterExpand.call(r);M(b,p,r)})});F=f.find("div."+b.summaryClass);b.userCollapse&&!f.find("span."+b.lessClass).length&&f.find(u).append('<span class="'+b.lessClass+'">'+b.userCollapsePrefix+'<a href="#">'+b.userCollapseText+"</a></span>");f.find("span."+
b.lessClass+" a").unbind("click.expander").bind("click.expander",function(j){j.preventDefault();clearTimeout(A);j=c(this).closest(u);z(b,j);q.onCollapse&&b.onCollapse.call(r,true)})}})},destroy:function(){if(this.data("expander")){this.removeData("expander");this.each(function(){var a=c(this),d=c.meta?c.extend({},o,a.data()):o,g=a.find("."+d.detailClass).contents();a.find("."+d.moreClass).remove();a.find("."+d.summaryClass).remove();a.find("."+d.detailClass).after(g).remove();a.find("."+d.lessClass).remove()})}}};
l[v]&&l[v].call(this);return this};c.fn.expander.defaults=c.expander.defaults})(jQuery);
