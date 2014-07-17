/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
function Viewer(c){function p(){return document.isFullScreen||document.mozFullScreen||document.webkitIsFullScreen}function u(a){var b=E.options,c,f=!1,d;for(d=0;d<b.length;d+=1)c=b[d],c.value!==a?c.selected=!1:f=c.selected=!0;return f}function v(a,c,d){a!==b.getZoomLevel()&&(b.setZoomLevel(a),d=document.createEvent("UIEvents"),d.initUIEvent("scalechange",!1,!1,window,0),d.scale=a,d.resetAutoSettings=c,window.dispatchEvent(d))}function w(){var a;if(c.onScroll)c.onScroll();c.getPageInView&&(a=c.getPageInView())&&
(e=a,document.getElementById("pageNumber").value=a)}function x(a){window.clearTimeout(y);y=window.setTimeout(function(){w()},a)}function g(a,b,g){var f,e;if(f="custom"===a?parseFloat(document.getElementById("customScaleOption").textContent)/100:parseFloat(a))v(f,!0,g);else{f=d.clientWidth-k;e=d.clientHeight-k;switch(a){case "page-actual":v(1,b,g);break;case "page-width":c.fitToWidth(f);break;case "page-height":c.fitToHeight(e);break;case "page-fit":c.fitToPage(f,e);break;case "auto":c.isSlideshow()?
c.fitToPage(f+k,e+k):c.fitSmart(f)}u(a)}x(300)}function q(){l&&!p()&&b.togglePresentationMode()}function r(){m&&(s.className="touched",window.clearTimeout(z),z=window.setTimeout(function(){s.className=""},2E3))}var b=this,k=40,l=!1,A=!1,m=!1,t,B,d=document.getElementById("canvasContainer"),s=document.getElementById("overlayNavigator"),C=document.getElementById("toolbarLeft"),F=document.getElementById("toolbarMiddleContainer"),E=document.getElementById("scaleSelect"),D,n=[],e,y,z;this.initialize=function(){var a=
String(document.location),h=a.indexOf("#"),a=a.substr(h+1);-1===h||0===a.length?console.log("Could not parse file path argument."):(B=document.getElementById("viewer"),t=a,D=t.replace(/^.*[\\\/]/,""),document.title=D,document.getElementById("documentName").innerHTML=document.title,c.onLoad=function(){(m=c.isSlideshow())?(d.style.padding=0,C.style.visibility="visible"):(F.style.visibility="visible",c.getPageInView&&(C.style.visibility="visible"));A=!0;n=c.getPages();document.getElementById("numPages").innerHTML=
"of "+n.length;b.showPage(1);g("auto");d.onscroll=w;x()},c.initialize(d,a))};this.showPage=function(a){0>=a?a=1:a>n.length&&(a=n.length);c.showPage(a);e=a;document.getElementById("pageNumber").value=e};this.showNextPage=function(){b.showPage(e+1)};this.showPreviousPage=function(){b.showPage(e-1)};this.download=function(){var a=t.split("#")[0];window.open(a+"#viewer.action=download","_parent")};this.toggleFullScreen=function(){var a=B;p()?document.cancelFullScreen?document.cancelFullScreen():document.mozCancelFullScreen?
document.mozCancelFullScreen():document.webkitCancelFullScreen&&document.webkitCancelFullScreen():a.requestFullScreen?a.requestFullScreen():a.mozRequestFullScreen?a.mozRequestFullScreen():a.webkitRequestFullScreen&&a.webkitRequestFullScreen()};this.togglePresentationMode=function(){var a=document.getElementById("titlebar"),h=document.getElementById("toolbarContainer"),e=document.getElementById("overlayCloseButton");l?(a.style.display=h.style.display="block",e.style.display="none",d.className="",d.onmouseup=
function(){},d.oncontextmenu=function(){},d.onmousedown=function(){},g("auto"),m=c.isSlideshow()):(a.style.display=h.style.display="none",e.style.display="block",d.className="presentationMode",m=!0,d.onmousedown=function(a){a.preventDefault()},d.oncontextmenu=function(a){a.preventDefault()},d.onmouseup=function(a){a.preventDefault();1===a.which?b.showNextPage():b.showPreviousPage()},g("page-fit"));l=!l};this.getZoomLevel=function(){return c.getZoomLevel()};this.setZoomLevel=function(a){c.setZoomLevel(a)};
this.zoomOut=function(){var a=(b.getZoomLevel()/1.1).toFixed(2),a=Math.max(0.25,a);g(a,!0)};this.zoomIn=function(){var a=(1.1*b.getZoomLevel()).toFixed(2),a=Math.min(4,a);g(a,!0)};(function(){b.initialize();document.cancelFullScreen||(document.mozCancelFullScreen||document.webkitCancelFullScreen)||(document.getElementById("fullscreen").style.visibility="hidden");document.getElementById("overlayCloseButton").addEventListener("click",b.toggleFullScreen);document.getElementById("fullscreen").addEventListener("click",
b.toggleFullScreen);document.getElementById("presentation").addEventListener("click",function(){p()||b.toggleFullScreen();b.togglePresentationMode()});document.addEventListener("fullscreenchange",q);document.addEventListener("webkitfullscreenchange",q);document.addEventListener("mozfullscreenchange",q);document.getElementById("download").addEventListener("click",function(){b.download()});document.getElementById("zoomOut").addEventListener("click",function(){b.zoomOut()});document.getElementById("zoomIn").addEventListener("click",
function(){b.zoomIn()});document.getElementById("previous").addEventListener("click",function(){b.showPreviousPage()});document.getElementById("next").addEventListener("click",function(){b.showNextPage()});document.getElementById("previousPage").addEventListener("click",function(){b.showPreviousPage()});document.getElementById("nextPage").addEventListener("click",function(){b.showNextPage()});document.getElementById("pageNumber").addEventListener("change",function(){b.showPage(this.value)});document.getElementById("scaleSelect").addEventListener("change",
function(){g(this.value)});d.addEventListener("click",r);s.addEventListener("click",r);window.addEventListener("scalechange",function(a){var b=document.getElementById("customScaleOption"),c=u(String(a.scale));b.selected=!1;c||(b.textContent=Math.round(1E4*a.scale)/100+"%",b.selected=!0)},!0);window.addEventListener("resize",function(a){A&&(document.getElementById("pageWidthOption").selected||document.getElementById("pageAutoOption").selected)&&g(document.getElementById("scaleSelect").value);r()});
window.addEventListener("keydown",function(a){var c=a.shiftKey;switch(a.keyCode){case 38:case 37:b.showPreviousPage();break;case 40:case 39:b.showNextPage();break;case 32:c?b.showPreviousPage():b.showNextPage()}})})()};
