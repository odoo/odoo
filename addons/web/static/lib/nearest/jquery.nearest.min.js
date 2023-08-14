/*!
 * jQuery Nearest plugin v1.2.1
 *
 * Finds elements closest to a single point based on screen location and pixel dimensions
 * http://gilmoreorless.github.com/jquery-nearest/
 * Open source under the MIT licence: http://gilmoreorless.mit-license.org/2011/
 *
 * Requires jQuery 1.4 or above
 * Also supports Ben Alman's "each2" plugin for faster looping (if available)
 */
;(function(e,t){function r(t,r,i){t||(t="div");var s=e(r.container),o=s.offset()||{left:0,top:0},u=[o.left+s.width(),o.top+s.height()],a={x:0,y:1,w:0,h:1},f,l;for(f in a)a.hasOwnProperty(f)&&(l=n.exec(r[f]),l&&(r[f]=u[a[f]]*l[1]/100));var c=e(t),h=[],p=!!r.furthest,d=!!r.checkHoriz,v=!!r.checkVert,m=p?0:Infinity,g=parseFloat(r.x)||0,y=parseFloat(r.y)||0,b=parseFloat(g+r.w)||g,w=parseFloat(y+r.h)||y,E=r.tolerance||0,S=!!e.fn.each2,x=Math.min,T=Math.max;!r.includeSelf&&i&&(c=c.not(i)),E<0&&(E=0),c[S?"each2":"each"](function(t,n){var r=S?n:e(this),i=r.offset(),s=i.left,o=i.top,u=r.outerWidth(),a=r.outerHeight(),f=s+u,l=o+a,c=T(s,g),N=x(f,b),C=T(o,y),k=x(l,w),L=N>=c,A=k>=C,O,M,_,D;if(d&&v||!d&&!v&&L&&A||d&&A||v&&L)O=L?0:c-N,M=A?0:C-k,_=L||A?T(O,M):Math.sqrt(O*O+M*M),D=p?_>=m-E:_<=m+E,D&&(m=p?T(m,_):x(m,_),h.push({node:this,dist:_}))});var N=h.length,C=[],k,L,A,O;if(N){p?(k=m-E,L=m):(k=m,L=m+E);for(A=0;A<N;A++)O=h[A],O.dist>=k&&O.dist<=L&&C.push(O.node)}return C}var n=/^([\d.]+)%$/;e.each(["nearest","furthest","touching"],function(n,i){var s={x:0,y:0,w:0,h:0,tolerance:1,container:document,furthest:i=="furthest",includeSelf:!1,checkHoriz:i!="touching",checkVert:i!="touching"};e[i]=function(n,i,o){if(!n||n.x===t||n.y===t)return e([]);var u=e.extend({},s,n,o||{});return e(r(i,u))},e.fn[i]=function(t,n){var i;if(t&&e.isPlainObject(t))return i=e.extend({},s,t,n||{}),this.pushStack(r(this,i));var o=this.offset(),u={x:o.left,y:o.top,w:this.outerWidth(),h:this.outerHeight()};return i=e.extend({},s,u,n||{}),this.pushStack(r(t,i,this))}})})(jQuery);