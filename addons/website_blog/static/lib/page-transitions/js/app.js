
/*    
      jQuery Setup                                                           
************************************************************************/ 
jQuery.ajaxSetup({
  cache: false
})

/*    
      ArticleAnimator Object                                                           
************************************************************************/ 
var ArticleAnimator = ArticleAnimator || {
  canScroll:          true,
  initialLoad:        true,
  animationDuration:  500,
  postCount:          5,
  currentPostIndex:   1,
  postCache:          {},
  pageTemplate:       null,
};

ArticleAnimator.load = function(){
  this.currentPostIndex = getURLIndex();
  this.makeSelections();
  $body.append( this.$current )
  $body.append( this.$next )

  var self = this;
  this.createPost({ type: 'current' }, function(){
    self.createPost({ type: 'next' }, function(){

      /* Selections. */
      self.refreshCurrentAndNextSelection();

      /* Push initial on to stack */
      history.pushState(pageState(), "", "#" + self.currentPostIndex)

      /* Bind to some events. */
      self.bindGotoNextClick();
      self.bindPopstate();
      self.bindWindowScroll();
    })
  })
}

ArticleAnimator.makeSelections = function(){
  this.$page         = $('.page');
  this.pageTemplate  = elementToTemplate( this.$page.clone());
  this.$current      = this.currentElementClone();
  this.$next         = this.nextElementClone();
}

ArticleAnimator.getPost = function(index, callback){
  callback = callback || $.noop;

  if ( this.postCache[index] ){
    callback( this.postCache[index] );
    return;
  }

  var self = this;
  openerp.jsonRpc("/blog_post/post/", 'call', {
        'blog': index,
    })
    .then(function (data) {
        if(!data)
            return;
        self.postCache[index] = data[0];
        callback(data[0])
    });
} 

ArticleAnimator.nextPostIndex = function(index){
  return (index === this.postCount) ? 1 : index + 1 
}

ArticleAnimator.createPost = function(opts, callback){
  opts      = opts || {};
  var self  = this;
  var type  = opts['type'] || 'next';

  if ( opts['fromTemplate'] ){
    $body.append( this.nextElementClone() );
    this['$' + type] = $('.' + type)
  }

  var index = (type == 'next') ? this.nextPostIndex( this.currentPostIndex) : this.currentPostIndex;
  this.getPost(index, function(d){
    self.contentizeElement(self['$' + type], d);
    callback && callback();
  });

}

ArticleAnimator.contentizeElement = function($el, d){
  $el.find('.big-image').css({ backgroundImage: (d.image)?"url(data:image/png;base64," + d.image + ")":""});
  $el.find('h1.title').html(d.title);
  $el.find('h2.description').html(d.title_secondary);
  $el.find('.content .text').html(d.content);
  $el.find('h4.byline time').html(d.date);
  $el.find('h4.byline .author').html(d.author);
  $el.find('h4.byline .author_image').html("<img class='img-circle' style='width: 3%; margin-right:10px;' src='" + d.author_image + "'/>")
}

ArticleAnimator.animatePage = function(callback){
  var self              = this;
  var translationValue  = this.$next.get(0).getBoundingClientRect().top;
  this.canScroll        = false;

  this.$current.addClass('fade-up-out');

  this.$next.removeClass('content-hidden next')
       .addClass('easing-upward')
       .css({ "transform": "translate3d(0, -"+ translationValue +"px, 0)" });

  setTimeout(function(){
      scrollTop();
      self.$next.removeClass('easing-upward')
      self.$current.remove();

      self.$next.css({ "transform": "" });
      self.$current = self.$next.addClass('current');
      
      self.canScroll = true;
      self.currentPostIndex = self.nextPostIndex( self.currentPostIndex );

      callback();
  }, self.animationDuration );
}

ArticleAnimator.bindGotoNextClick = function(){
  var self  = this;
  var e     = 'ontouchstart' in window ? 'touchstart' : 'click';

  this.$next.find('.big-image').on(e, function(e){
    e.preventDefault();
    $(this).unbind(e);

    self.animatePage(function(){
      self.createPost({ fromTemplate: true, type: 'next' });
      self.bindGotoNextClick();
      history.pushState( pageState(), '', "#" + self.currentPostIndex);
    });
  });
}

ArticleAnimator.bindPopstate = function(){
  var self = this;
  $window.on('popstate', function(e){
    
    if( !history.state || self.initialLoad ){
      self.initialLoad = false;
      return;
    }

    self.currentPostIndex = history.state.index;
    self.$current.replaceWith( history.state.current );
    self.$next.replaceWith( history.state.next );

    self.refreshCurrentAndNextSelection();
    self.createPost({ type: 'next' });
    self.bindGotoNextClick();
  });
}

ArticleAnimator.bindWindowScroll = function(){
  var self = this;
  $window.on('mousewheel', function(ev){
    if ( !self.canScroll ) 
      ev.preventDefault()
  })
}

ArticleAnimator.refreshCurrentAndNextSelection = function(){
  this.$current      = $('.page.current');
  this.$next         = $('.page.next');
}

ArticleAnimator.nextElementClone = function(){
  return this.$page.clone().removeClass('hidden').addClass('next content-hidden');
}

ArticleAnimator.currentElementClone = function(){
  return this.$page.clone().removeClass('hidden').addClass('current');
}

/*    
      Helper Functions.                                                      
************************************************************************/ 
function elementToTemplate($element){
  return $element.get(0).outerHTML;
}

function scrollTop(){
  $body.add($html).scrollTop(0);
}

function pageState(){
  return { index: ArticleAnimator.currentPostIndex, current: elementToTemplate(ArticleAnimator.$current), next: elementToTemplate(ArticleAnimator.$next) }
}

function getURLIndex(){
  return parseInt( (history.state && history.state.index) ||window.location.hash.replace('#', "") || ArticleAnimator.currentPostIndex );
}


/*    
      Document ready.                                                         
************************************************************************/ 
$(document).ready(function(){
  /* A couple of selections. */
  $body         = $('main');
  $window       = $(window);
  $html         = $(document.documentElement);

  /* Let's get it started. */
    ArticleAnimator.load();
})
