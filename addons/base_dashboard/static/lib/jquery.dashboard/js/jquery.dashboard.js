/*
 * dashboard 1.0
 * http://www.gxdeveloperweb.com/dashboard/
 *
 * Copyright (c) 2010 Mark Machielsen
 *
 * Dual licensed under the MIT and GPL licenses (same as jQuery):
 *   http://www.opensource.org/licenses/mit-license.php
 *   http://www.gnu.org/licenses/gpl.html
 *
 */
 
(function($) { // Create closure.

  // Constructor for dashboard object.
  $.fn.dashboard = function(options) {
    // Public properties of dashboard.
    var dashboard = {};
    var loading;
    var widgetDirectoryUrl;
    dashboard.layout;
    dashboard.element = this;
    dashboard.id = this.attr("id");
    dashboard.widgets = {};
    dashboard.widgetsToAdd = {};
    dashboard.widgetCategories = {};
    dashboard.initialized = false;

    // Public methods
    dashboard.serialize = function() { 
      dashboard.log('entering serialize function',1);
      var r = '{"layout": "' + dashboard.layout.id + '", "data" : [';
      // add al widgets in the right order
      var i=0;
      if ($('.' + opts.columnClass).length == 0) dashboard.log(opts.columnClass  + ' class not found',5);
      $('.' + opts.columnClass).each(function() {
        $(this).children().each(function() {
          if ($(this).hasClass(opts.widgetClass)) {
            if (i > 0) { r+= ','; }
            r+= (dashboard.getWidget($(this).attr("id"))).serialize();
            i++;
          }
        });    
      });
      r+= ']}';
      return r;    
    }

    dashboard.log = function(msg, level) {
      if (level >= opts.debuglevel && typeof console != 'undefined') {
        var l = '';
        if (level == 1) l = 'INFO';
        if (level == 2) l = 'EVENT';
        if (level == 3) l = 'WARNING';
        if (level == 5) l = 'ERROR';
        console.log(l + ' - ' + msg);      
      }    
    }
        
    dashboard.setLayout = function(layout) {   
      if (layout != null) {
        dashboard.log('entering setLayout function with layout ' + layout.id,1);
      } else {
        dashboard.log('entering setLayout function with layout null',1);
      }      
      dashboard.layout = layout;

      loading.remove();
      if (dashboard.layout != null) {
        if (typeof opts.layoutClass != 'undefined') {
          this.element.find('.' + opts.layoutClass).addClass(dashboard.layout.classname);
        } else {
          this.element.html(dashboard.layout.html);
        }
      }
      
      // make the columns sortable, see http://jqueryui.com/demos/sortable/ for explaination
      $('.' + opts.columnClass).sortable({
        connectWith: $('.' + opts.columnClass),
        opacity: opts.opacity,
        handle: '.' + opts.widgetHeaderClass,
        over: function(event, ui) { 
          $(this).addClass("selectedcolumn");
        },
        out: function(event, ui) { 
          $(this).removeClass("selectedcolumn");
        },
        receive: function(event, ui) {
          // update the column attribute for the widget
          var w = dashboard.getWidget(ui.item.attr("id"));
          w.column = getColumnIdentifier($(this).attr("class"));

          dashboard.log('dashboardStateChange event thrown for widget ' + w.id,2);        
          dashboard.element.trigger("dashboardStateChange",{"stateChange":"widgetMoved","widget":w});        

          dashboard.log('widgetDropped event thrown for widget ' + w.id,2);        
          w.element.trigger("widgetDropped",{"widget":w});
        },
        deactivate: function(event, ui) {  
          // This event is called for each column
          dashboard.log('Widget is dropped: check if the column is now empty.',1);        
          var childLength = $(this).children().length;
          if (childLength == 0) {
            dashboard.log('adding the empty text to the column',1);        
            $(this).html('<div class="emptycolumn">' + opts.emptyColumnHtml + '</div>');            
          } else {
            if (childLength == 2) {
              // remove the empty column HTML
              $(this).find('.emptycolumn').remove();          
            }
          }
        },
        start: function(event, ui) {
          ui.item.find('.' + opts.widgetTitleClass).addClass('noclick');
        },
        stop: function(event, ui) {
            //sorting changed (within one list)
            setTimeout(function(){
              ui.item.find('.' + opts.widgetTitleClass).removeClass('noclick');
             }, 300);
        }

      });
      
      fixSortableColumns();
      
      // trigger the dashboardLayoutLoaded event
      dashboard.log('dashboardLayoutLoaded event thrown',2);        
      dashboard.element.trigger("dashboardLayoutLoaded");      
    }
    
    // This is a workaround for the following problem: when I drag a widget from column2 to column1, sometimes the widget is
    // moved to column3, which is not visible
    function fixSortableColumns() {
      dashboard.log('entering fixSortableColumns function',1);
      $('.nonsortablecolumn').removeClass('nonsortablecolumn').addClass(opts.columnClass);            
      $('.' + opts.columnClass).filter(function() {return $(this).css("display") == 'none'}).addClass('nonsortablecolumn').removeClass(opts.columnClass);              
    }
    
    function getColumnIdentifier(classes) {
      dashboard.log('entering getColumnIdentifier function',1);
      var r;
      var s = classes.split(" ");
      for (var i = 0;i < s.length;i++) {
        if (s[i].indexOf(opts.columnPrefix) === 0) { r = s[i] };
      };
      return r.replace(opts.columnPrefix,'');
    }

    dashboard.loadLayout = function() {    
      dashboard.log('entering loadLayout function',1);
      if (typeof opts.json_data.url != 'undefined' && opts.json_data.url.length > 0) {
        // ajax option
        dashboard.log('Getting JSON feed : ' + opts.json_data.url,1);
        $.getJSON(opts.json_data.url, function(json) {
          if (json == null) {
            alert('Unable to get json. If you are using chrome: there is an issue with loading json with local files. It works on a server :-)',5);
            return;
          }
          // set the layout
          var currentLayout = (typeof dashboard.layout != 'undefined') ? dashboard.layout : getLayout(json.layout);
          dashboard.setLayout(currentLayout);         
          dashboard.loadWidgets(json.data);
        });      
      } else {
        // set the layout
//        var currentLayout;
//        if(typeof dashboard.layout != 'undefined') {
//            currentLayout = dashboard.layout
//        }
        var currentLayout = (typeof dashboard.layout != 'undefined') ? dashboard.layout : getLayout(opts.json_data.layout);
        dashboard.setLayout(currentLayout);
        dashboard.loadWidgets(opts.json_data.data);
      }
    };
    
    dashboard.addWidget = function(obj, column) {
      dashboard.log('entering addWidget function',1);
      // add the widget to the column
      var wid = obj.id;

      // check if the widget is already registered and available in the dom
      if (typeof dashboard.widgets[wid] != 'undefined' && $('#' + wid).length > 0) {
        var wi = $('#' + wid);
        column = dashboard.widgets[wid].column;

        // add it to the column
        wi.appendTo(column);    

      } else {
        // build the widget    
        dashboard.log('Applying template : ' + opts.widgetTemplate,1);
        if ($('#' + opts.widgetTemplate).length == 0) dashboard.log('Template "' + opts.widgetTemplate + ' not found',5);
        var widgetStr = tmpl($('#' + opts.widgetTemplate).html(), obj);
        var wi = $(widgetStr);

        // add it to the column
        wi.appendTo(column);    

        dashboard.widgets[wid] = widget({
          id: wid,
          element: wi,
          column: obj.column,
          url: (typeof obj.url != 'undefined' ? obj.url : null),
          editurl: obj.editurl,
          title: obj.title,
          open: obj.open,
          metadata: obj.metadata
        });
      }

      dashboard.log('widgetAdded event thrown for widget ' + wid,2);        
      dashboard.widgets[wid].element.trigger("widgetAdded", {"widget":dashboard.widgets[wid]});

      if (dashboard.initialized) {
        dashboard.log('dashboardStateChange event thrown for widget ' + wid,2);        
        dashboard.element.trigger("dashboardStateChange",{"stateChange":"widgetAdded","widget":wi});
      }
    }        

    dashboard.loadWidgets = function(data) {
      dashboard.log('entering loadWidgets function',1);
      dashboard.element.find('.' + opts.columnClass).empty();


      // This is for the manual feed
      $(data).each(function() {
        var column = this.column;        
        dashboard.addWidget(this, dashboard.element.find('.' + opts.columnPrefix + column));
      }); // end loop for widgets
      
      // check if there are widgets in the temp dashboard which needs to be moved
      // this is not the correct place, but otherwise we are too late
      
      // check if there are still widgets in the temp
      $('#tempdashboard').find('.' + opts.widgetClass).each(function() {
        // append it to the first column
        var firstCol = dashboard.element.find('.' + opts.columnClass + ':first');
        $(this).appendTo(firstCol);
        
        // set the new column
        dashboard.getWidget($(this).attr("id")).column = firstCol.attr("id");
      });
      $('#tempdashboard').remove();

      // add the text to the empty columns
      $('.' + opts.columnClass).each(function() {
        if ($(this).children().length == 0) {
          $(this).html('<div class="emptycolumn">' + opts.emptyColumnHtml + '</div>');
        }
      });            
      
      dashboard.initialized = true;
    };
    
    dashboard.init = function() {
      dashboard.log('entering init function',1);
      // load the widgets as fast as we can. After that add the binding
      dashboard.loadLayout();    
    }
    
    dashboard.getWidget = function(id) {
      dashboard.log('entering getWidget function',1);
      var wi = dashboard.widgets[id];
      if (typeof wi != 'undefined') {
        return wi;
      } else {
        return null;
      }
    }
    
    
    // Merge in the caller's options with the defaults.
    var opts = $.extend({}, $.fn.dashboard.defaults, options);
    var addOpts = $.extend({}, $.fn.dashboard.defaults.addWidgetSettings, options.addWidgetSettings);
    var layoutOpts = $.extend({}, $.fn.dashboard.defaults.editLayoutSettings, options.editLayoutSettings);
    
    // Execution 'forks' here and restarts in init().  Tell the user we're busy with a loading.
    var loading = $(opts.loadingHtml).appendTo(dashboard.element);
    
    /**
     * widget object
     *    Private sub-class of dashboard
     * Constructor starts
     */
    function widget(widget) {
    
      dashboard.log('entering widget constructor',1);
      // Merge default options with the options defined for this widget.
      widget = $.extend({}, $.fn.dashboard.widget.defaults, widget);
      
      // public functions
      widget.openContent = function() {
        // hide the open link, show the close link
        widget.element.find('.widgetOpen').hide();
        widget.element.find('.widgetClose').show();

        dashboard.log('entering openContent function',1);
        widget.open = true;
        if (!widget.loaded) {
          // load the content in the widget if the state == open
          if (this.url != '' && this.url != null && typeof this.url != 'undefined') {
            // add the loading
            $(opts.loadingHtml).appendTo(widget.element.find('.' + opts.widgetContentClass));

            dashboard.log('widgetShow event thrown for widget ' + widget.id,2);        
            widget.element.trigger("widgetShow", {"widget":widget});
            
            widget.element.find('.' + opts.widgetContentClass).load(this.url, function(response, status, xhr) {
              if (status == "error") {
                widget.element.find('.' + opts.widgetContentClass).html(opts.widgetNotFoundHtml);
              }
              widget.loaded = true;
              dashboard.log('widgetLoaded event thrown for widget ' + widget.id,2);        
              widget.element.trigger("widgetLoaded", {"widget":widget});
            });
          } else {          
            dashboard.log('widgetShow event thrown for widget ' + widget.id,2);        
            widget.element.trigger("widgetShow", {"widget":widget});

            dashboard.log('widgetLoaded event thrown',2);                  
            widget.element.trigger("widgetLoaded", {"widget":widget});
          }
        } else {
          dashboard.log('widgetShow event thrown for widget ' + widget.id,2);        
          widget.element.trigger("widgetShow", {"widget":widget});
        }
        if (dashboard.initialized) {
          dashboard.log('dashboardStateChange event thrown for widget ' + widget.id,2);        
          dashboard.element.trigger("dashboardStateChange",{"stateChange":"widgetOpened","widget":widget});        
        }
      };
      widget.refreshContent = function() {
        dashboard.log('entering refreshContent function',1);
        widget.loaded = false;
        if (widget.open) {
          widget.openContent();
        }
      }
      widget.setTitle = function(newTitle){
        dashboard.log('entering setTitle function',1);
        widget.title=newTitle;
        widget.element.find('.' + opts.widgetTitleClass).html(newTitle);
        if (dashboard.initialized) {
          dashboard.log('dashboardStateChange event thrown for widget ' + widget.id,2);        
          dashboard.element.trigger("dashboardStateChange",{"stateChange":"titleChanged","widget":widget}); 
        }          
      }
      widget.closeContent = function() {
        dashboard.log('entering closeContent function',1);
        widget.open = false;

        dashboard.log('widgetHide event thrown for widget ' + widget.id,2);        
        widget.element.trigger("widgetHide", {"widget":widget});

        // show the open link, hide the close link
        widget.element.find('.widgetOpen').show();
        widget.element.find('.widgetClose').hide();

        dashboard.log('dashboardStateChange event thrown for widget ' + widget.id,2);        
        dashboard.element.trigger("dashboardStateChange",{"stateChange":"widgetClosed","widget":widget});
      };
      widget.addMetadataValue = function(name, value) {
        dashboard.log('entering addMetadataValue function',1);
        if (typeof widget.metadata == 'undefined') {
          widget.metadata = {};
        }
        widget.metadata[name] = value;
        dashboard.log('dashboardStateChange event thrown for widget ' + widget.id,2);        
        dashboard.element.trigger("dashboardStateChange",{"stateChange":"metadataChanged","widget":widget});
      };
      widget.openMenu = function() {
        dashboard.log('entering openMenu function',1);
        widget.element.find('.' + opts.menuClass).show();
      };
      widget.closeMenu = function() {
        dashboard.log('entering closeMenu function',1);
        widget.element.find('.' + opts.menuClass).hide();
      };
      widget.remove = function() {
        dashboard.log('entering remove function',1);
        widget.element.remove();      
        dashboard.log('widgetDeleted event thrown for widget ' + widget.id,2);        
        widget.element.trigger('widgetDeleted', {"widget":widget});        

        dashboard.log('dashboardStateChange event thrown for widget ' + widget.id,2);        
        dashboard.element.trigger("dashboardStateChange",{"stateChange":"widgetRemoved","widget":widget});
      };
      widget.serialize = function() {
        dashboard.log('entering serialize function',1);
        var r = '{"title" : "' + widget.title + '", "id" : "' + widget.id + '", "column" : "' + widget.column + '","editurl" : "' + widget.editurl + '","open" : ' + widget.open + ',"url" : "' + widget.url + '"';
        
        if (typeof widget.metadata != 'undefined') {
          r+= ',"metadata":{'
          var obj = widget.metadata;
          var i=0;
          for(var item in obj) {
            if (i > 0) { r+= ',' };
            
            // FIXME: support for more than string, eg numbers subobjects
            r+= '"' + item + '":"' + obj[item] + '"';
            i++;
          }
          r+= '}'
          
        }
        
        r += '}';
        return r;      
      };
      widget.openFullscreen = function() {
        dashboard.log('entering openFullscreen function',1);
        widget.fullscreen = true;
        
        // create a clone
        var clone = widget.element.clone();

        // move the dashboard 
        var temp = $('<div style="display:none" id="tempdashboard_' + dashboard.id + '"></div>');
        temp.appendTo($("body"));
        dashboard.element.children().appendTo(temp);

        // add the clone to the dashboard
        var fs = $('<ul id="fullscreen_' + dashboard.id + '"></ul>');
        fs.appendTo(dashboard.element);
        clone.appendTo(fs);
        
      };
      widget.closeFullscreen = function() {
        dashboard.log('entering closeFullscreen function',1);
        widget.fullscreen = false;

        // remove the fullscreen
        $('#fullscreen_' + dashboard.id).remove();

        // move the content from the tempdashboard back
        $('#tempdashboard_' + dashboard.id).children().appendTo(dashboard.element);
        $('#tempdashboard_' + dashboard.id).remove();
        
      };      
      widget.openSettings = function() {
        dashboard.log('entering openSettings function',1);
        widget.element.find('.' + opts.widgetContentClass).load(widget.editurl);
      };
      
      // called when widget is initialized
      if (widget.open) {
        widget.openContent();
      }

      widget.initialized = true;

      dashboard.log('widgetInitialized event thrown',2);                  
      widget.element.trigger("widgetInitialized", {"widget":widget});

      return widget;
    };
    

    // FIXME: can this be done easier??
    function getLayout(id) {
      dashboard.log('entering getLayout function',1);
      var r = null;
      var first = null;
      if (typeof opts.layouts != 'undefined') {

        $.each(opts.layouts,function(i, item) {
          if (i == 0) { first = item; }
          if (item.id == id) {
            r = item;
          }
        });
      }
      if (r == null) { r = first }
      return r;
    }
    
    
    $('#' + dashboard.id + ' .menutrigger').live('click', function() {
      dashboard.log('widgetOpenMenu event thrown for widget ' + widget.id,2);
      var wi = dashboard.getWidget($(this).closest('.' + opts.widgetClass).attr("id"));
      
      wi.element.trigger('widgetOpenMenu', {"widget":wi});      
      return false;
    });
        
    // add event handlers to the menu
    $('#' + dashboard.id + ' .' + opts.widgetFullScreenClass).live('click',function(e) {        
      // close the menu
      dashboard.log('widgetCloseMenu event thrown for widget ' + widget.id,2);        
      var wi = dashboard.getWidget($(this).closest('.' + opts.widgetClass).attr("id"));
      wi.element.trigger('widgetCloseMenu', {"widget":wi});      
            
      if (wi.fullscreen) {
        dashboard.log('widgetCloseFullScreen event thrown for widget ' + wi.id,2);        
        wi.element.trigger('widgetCloseFullScreen', {"widget":wi});
      } else {
        dashboard.log('widgetOpenFullScreen event thrown for widget ' + wi.id,2);        
        wi.element.trigger('widgetOpenFullScreen', {"widget":wi});
      }
      return false;
    });

    $('#' + dashboard.id + ' .controls li').live('click',function(e) {        
      // close the menu
      dashboard.log('widgetCloseMenu event thrown for widget ' + widget.id,2);        

      var wi = dashboard.getWidget($(this).closest('.' + opts.widgetClass).attr("id"));
      wi.element.trigger('widgetCloseMenu', {"widget":wi});      
      
      // use the class on the li to determine what action to trigger
      dashboard.log($(this).attr('class') + ' event thrown for widget ' + widget.id,2);        
      
      var wi = dashboard.getWidget($(this).closest('.' + opts.widgetClass).attr("id"));
      wi.element.trigger($(this).attr('class'), {"widget":wi});
      return false;
    });
    
    // add the menu events (by default triggers are connected in dashboard_jsonfeed)
    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetCloseMenu',function(e,o) {
      dashboard.log("Closing menu " + $(this).attr("id"),1);
      o.widget.closeMenu();
    });

    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetOpenMenu',function(e,o) {
      dashboard.log("Opening menu " + $(this).attr("id"),1);
      o.widget.openMenu();
    });

    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetDelete',function(e,o) {
      if (confirm(opts.deleteConfirmMessage)) {
        dashboard.log("Removing widget " + $(this).attr("id"),1);
        o.widget.remove();
      }      
    });

    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetRefresh',function(e,o) {
      o.widget.refreshContent();
    });
    
    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetSetTitle',function(event, o) {
      o.widget.setTitle(o.title);
    });

    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetClose',function(e,o) {
      dashboard.log("Closing widget " + $(this).attr("id"),1);
      o.widget.closeContent();
    });

    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetOpen',function(e,o) {    
      dashboard.log("Opening widget " + $(this).attr("id"),1);
      o.widget.openContent();
    });

    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetShow',function() {    
      $(this).find('.' + opts.widgetContentClass).show();
    });

    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetHide',function() {    
      $(this).find('.' + opts.widgetContentClass).hide();
    });
    
    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetAddMetadataValue',function(e,o) {
      dashboard.log("Changing metadata for widget " + $(this).attr("id") + ", metadata name: " + o.name + ", value: " + o.value, 1);
      o.widget.addMetadataValue(o.name, o.value);
    });
    
    // Define a toggle event when clicking at the header
    $('#' + dashboard.id + ' .' + opts.widgetTitleClass).live('click',function(e) {
      dashboard.log("Click on the header detected for widget " + $(this).attr("id"),1);
      if (!$(this).hasClass('noclick')) {
        var wi = dashboard.getWidget($(this).closest('.' + opts.widgetClass).attr("id"));
        if (wi.open) {
          dashboard.log('widgetClose event thrown for widget ' + wi,2);        
          wi.element.trigger('widgetClose', {"widget":wi});      
        } else {
          dashboard.log('widgetOpen event thrown for widget ' + wi,2);        
          wi.element.trigger('widgetOpen', {"widget":wi});
        }
      }
      return false;
    });
    
    $('#' + dashboard.id + ' .' + opts.widgetHeaderClass).live('mouseover',function () {
      $(this).find('.' + opts.iconsClass).removeClass("hidden");
    });
        
    $('#' + dashboard.id + ' .' + opts.widgetHeaderClass).live('mouseout', function () {
      $(this).find('.' + opts.iconsClass).addClass("hidden");
    });

    $('body').click(function() {
      $('.' + opts.menuClass).hide();
    });

    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetOpenFullScreen',function(e,o) {
      o.widget.openFullscreen();
    });

    $('.' + opts.widgetClass).live('widgetCloseFullScreen',function(e,o) {
      o.widget.closeFullscreen();      
    });

    $('#' + dashboard.id + ' .' + opts.widgetClass).live('widgetEdit',function(e,o) {
      o.widget.openSettings();      
    });
        
    if ($('#' + addOpts.dialogId).length == 0) dashboard.log('Unable to find ' + addOpts.dialogId,5);
    $('#' + addOpts.dialogId).dialog({
      autoOpen: false,
      height: 414,
      width: 550,
      modal: true,
      buttons: {
        Cancel: function() {
          $(this).dialog('close');
        }
      },
      close: function() {
        //close
      }
    });

    if ($('#' + layoutOpts.dialogId).length == 0) dashboard.log('Unable to find ' + layoutOpts.dialogId,5);
    $('#' + layoutOpts.dialogId).dialog({
      autoOpen: false,
      height: 300,
      width: 600,
      modal: true
    });

    $('.' + layoutOpts.openDialogClass).live('click', function(){
      dashboard.log('dashboardOpenLayoutDialog event thrown',2);        
      dashboard.element.trigger("dashboardOpenLayoutDialog");
      return false;
    });
    
    dashboard.element.live('dashboardOpenLayoutDialog', function(){        
      dashboard.log('Opening dialog ' + layoutOpts.dialogId,1);
      $('#' + layoutOpts.dialogId).dialog('open');

      // add the layout images
      var h = $('#' + layoutOpts.dialogId).find('.' + layoutOpts.layoutClass);
      h.empty();
      if (h.children().length == 0) {
        dashboard.log('Number of layouts : ' + opts.layouts.length,1);
        $.each(opts.layouts,function(i, item) {
          dashboard.log('Applying template : ' + layoutOpts.layoutTemplate,1);
          if ($('#' + layoutOpts.layoutTemplate).length == 0) dashboard.log('Template "' + layoutOpts.layoutTemplate + ' not found',5);
          h.append(tmpl($('#' + layoutOpts.layoutTemplate).html(), item));
        });
      }
      
      // set the selected class for the selected layout
      $('.' + layoutOpts.selectLayoutClass).removeClass(layoutOpts.selectedLayoutClass);
      $('#' + dashboard.layout.id).addClass(layoutOpts.selectedLayoutClass);
      
      bindSelectLayout();
    });


    dashboard.element.live('dashboardStateChange', function(){   
       if (typeof opts.stateChangeUrl != 'undefined' && opts.stateChangeUrl != null && opts.stateChangeUrl != '') {
        $.ajax({type: 'POST',
          url: opts.stateChangeUrl, 
          data: { dashboard: dashboard.element.attr("id"), settings: dashboard.serialize() }, 
          success: function(data){ 
            if (data == "NOK" || data.indexOf('<response>NOK</response>') != -1){ 
              dashboard.log('dashboardSaveFailed event thrown',2);        
              dashboard.element.trigger("dashboardSaveFailed");      
            } else {
              dashboard.log('dashboardSuccessfulSaved event thrown',2);        
              dashboard.element.trigger("dashboardSuccessfulSaved");      
            }
          },
          error: function(XMLHttpRequest, textStatus, errorThrown){ 
            dashboard.log('dashboardSaveFailed event thrown',2);        
            dashboard.element.trigger("dashboardSaveFailed");      
          },
          dataType: "text"
        });
      }
    });
    

    dashboard.element.live('dashboardCloseLayoutDialog', function(){   
      // close the dialog
      $('#' + layoutOpts.dialogId).dialog('close');
    });

    // FIXME: why doesn't the live construct work in this case
    function bindSelectLayout() {
      if ($('.' + layoutOpts.selectLayoutClass).length == 0) dashboard.log('Unable to find ' + layoutOpts.selectLayoutClass,5);
      $('.' + layoutOpts.selectLayoutClass).bind('click', function(e){    
        var currentLayout = dashboard.layout;
        
        dashboard.log('dashboardCloseLayoutDialog event thrown',2);        
        dashboard.element.trigger('dashboardCloseLayoutDialog');

        // Now set the new layout
        var newLayout = getLayout($(this).attr("id"));
        dashboard.layout = newLayout;

        // remove the class of the old layout
        if (typeof opts.layoutClass != 'undefined') {
          dashboard.element.find('.' + opts.layoutClass).removeClass(currentLayout.classname).addClass(newLayout.classname);
          
          fixSortableColumns();
          
          // check if there are widgets in hidden columns, move them to the first column
          if ($('.' + opts.columnClass).length == 0) dashboard.log('Unable to find ' + opts.columnClass,5);
          dashboard.element.find('.' + opts.columnClass).each(function() {
            if ($(this).css("display") == "none") {
              // move the widgets to the first column
              $(this).children().appendTo(dashboard.element.find('.' + opts.columnClass + ':first'));
            }
            
            $('.emptycolumn').remove();
            // add the text to the empty columns
            $('.' + opts.columnClass).each(function() {
              if ($(this).children().length == 0) {
                $(this).html('<div class="emptycolumn">' + opts.emptyColumnHtml + '</div>');
              }
            });            
            
            
          });
          
        } else {
          // set the new layout, but first move the dashboard to a temp
          var temp = $('<div style="display:none" id="tempdashboard"></div>');
          temp.appendTo($("body"));

          dashboard.element.children().appendTo(temp);

          // reload the dashboard
          dashboard.init();
        }

        // throw an event upon changing the layout. 
        dashboard.log('dashboardChangeLayout event thrown',2);        
        dashboard.element.trigger('dashboardLayoutChanged');

      });
      return false;
    }    

    $('.' + addOpts.selectCategoryClass).live('click', function(){     
      dashboard.log('addWidgetDialogSelectCategory event thrown',2);        
      dashboard.element.trigger('addWidgetDialogSelectCategory', {"category":$(this)});          
      return false;
    });

    dashboard.element.live('addWidgetDialogSelectCategory', function(e, obj){
      // remove the category selection
      $('.' + addOpts.selectCategoryClass).removeClass(addOpts.selectedCategoryClass);
      
      // empty the widgets div
      $('#' + addOpts.dialogId).find('.' + addOpts.widgetClass).empty();
    
      // select the category
      $(obj.category).addClass(addOpts.selectedCategoryClass);
      
      // get the widgets
      url = dashboard.widgetCategories[$(obj.category).attr("id")];

      dashboard.log('Getting JSON feed : ' + url,1);
      $.getJSON(url, {"cache":true}, function(json) {      
        // load the widgets from the category        
        if (json.data == 0) dashboard.log('Empty data returned',3);
        $.each(json.data, function(i,item){
          dashboard.widgetsToAdd[item.id] = item;

          dashboard.log('Applying template : ' + addOpts.widgetTemplate,1);
          if ($('#' + addOpts.widgetTemplate).length == 0) dashboard.log('Template "' + addOpts.widgetTemplate + ' not found',5);
          var html = tmpl($('#' + addOpts.widgetTemplate).html(), item);
          $('#' + addOpts.dialogId).find('.' + addOpts.widgetClass).append(html);        
        });
      });
      
      dashboard.log('addWidgetDialogWidgetsLoaded event thrown',2);        
      dashboard.element.trigger('addWidgetDialogWidgetsLoaded');    
    });


    $('.' + addOpts.addWidgetClass).live('click', function(){      
      var widget = dashboard.widgetsToAdd[$(this).attr("id").replace('addwidget','')];
      dashboard.log('dashboardAddWidget event thrown',2);        
      dashboard.element.trigger('dashboardAddWidget', {"widget":widget});    

      dashboard.log('dashboardCloseWidgetDialog event thrown',2);        
      dashboard.element.trigger('dashboardCloseWidgetDialog');
      return false;
    });

    $('.' + addOpts.openDialogClass).live('click', function(){
      dashboard.log('dashboardOpenWidgetDialog event thrown',2);        
      dashboard.element.trigger('dashboardOpenWidgetDialog');
      return false;
    });
    
    dashboard.element.live('dashboardCloseWidgetDialog', function(){   
      // close the dialog
      $('#' + addOpts.dialogId).dialog('close');
    });
        
    dashboard.element.live('dashboardOpenWidgetDialog', function(){
    
      //remove existing categories/widgets from the DOM, to prevent duplications
      $('#' + addOpts.dialogId).find('.' + addOpts.categoryClass).empty();
      $('#' + addOpts.dialogId).find('.' + addOpts.widgetClass).empty();

      dashboard.log('Opening dialog ' + addOpts.dialogId,1);
      $('#' + addOpts.dialogId).dialog('open');

      dashboard.log('Getting JSON feed : ' + addOpts.widgetDirectoryUrl,1);
      $.getJSON(addOpts.widgetDirectoryUrl, function(json) {      
        if (json.category == 0) dashboard.log('Empty data returned',3);
        $.each(json.category, function(i,item){
          // Add the categories to the dashboard
          dashboard.widgetCategories[item.id] = item.url;
        
          dashboard.log('Applying template : ' + addOpts.categoryTemplate,1);
          if ($('#' + addOpts.categoryTemplate).length == 0) dashboard.log('Template "' + addOpts.categoryTemplate + ' not found',5);
          var html = tmpl($('#' + addOpts.categoryTemplate).html(),item);
          $('#' + addOpts.dialogId).find('.' + addOpts.categoryClass).append(html);        
        });        
        dashboard.log('addWidgetDialogCategoriesLoaded event thrown',2);        
        dashboard.element.trigger('addWidgetDialogCategoriesLoaded');    

        dashboard.log('addWidgetDialogSelectCategory event thrown',2);        
        dashboard.element.trigger('addWidgetDialogSelectCategory', {"category":$('#' + addOpts.dialogId).find('.' + addOpts.categoryClass + '>li:first')});    
        
      });
            
    });
     
    return dashboard;
  };

    
  // Public static properties of dashboard.  Default settings.
  $.fn.dashboard.defaults = {
    debuglevel:3,
    json_data: {},
    simple_data: {},
    loadingHtml: '<div class="loading"><img alt="Loading, please wait" src="../themes/default/loading.gif" /><p>Loading...</p></div>',
    emptyColumnHtml: 'Drag your widgets here',
    widgetTemplate: 'widgettemplate',
    columnPrefix: 'column-',
    opacity:"0.2",
    deleteConfirmMessage: "Are you sure you want to delete this widget?",
    widgetNotFoundHtml: "The content of this widget is not available anymore. You may remove this widget.",
    columnClass: 'column',
    widgetClass: 'widget',
    menuClass: 'controls',
    widgetContentClass: 'widgetcontent',
    widgetTitleClass: 'widgettitle',
    widgetHeaderClass: 'widgetheader',
    widgetFullScreenClass: 'widgetopenfullscreen',
    iconsClass: 'icons',
    stateChangeUrl: '',
    
    addWidgetSettings: {
      openDialogClass: 'openaddwidgetdialog',
      addWidgetClass: 'addwidget',
      selectCategoryClass: 'selectcategory',
      selectedCategoryClass: 'selected',
      categoryClass: 'categories',
      widgetClass: 'widgets',
      
      dialogId: 'addwidgetdialog',
      
      categoryTemplate: 'categorytemplate',
      widgetTemplate: 'addwidgettemplate'
    },
    editLayoutSettings: {
      dialogId: 'editLayout',
      layoutClass: 'layoutselection',
      selectLayoutClass: 'layoutchoice',
      selectedLayoutClass: 'selected',
      openDialogClass: 'editlayout',
      layoutTemplate: 'selectlayouttemplate'
    }
    

  };

  // Default widget settings.
  $.fn.dashboard.widget = {
    defaults: {
      open: true,
      fullscreen: false,
      loaded: false,
      url: '',
      metadata: {}
    }
  };

})(jQuery); // end of closure


// Simple JavaScript Templating
// John Resig - http://ejohn.org/ - MIT Licensed
(function(){
  var cache = {};
 
  this.tmpl = function tmpl(str, data){
    // Figure out if we're getting a template, or if we need to
    // load the template - and be sure to cache the result.

    var fn = !/\W/.test(str) ?
      cache[str] = cache[str] ||
        tmpl(document.getElementById(str).innerHTML) :
     
      // Generate a reusable function that will serve as a template
      // generator (and which will be cached).
      new Function("obj",
        "var p=[],print=function(){p.push.apply(p,arguments);};" +
       
        // Introduce the data as local variables using with(){}
        "with(obj){p.push('" +
       
        // Convert the template into pure JavaScript
        str
          .replace(/[\r\t\n]/g, " ")
          .split("<%").join("\t")
          .replace(/((^|%>)[^\t]*)'/g, "$1\r")
          .replace(/\t=(.*?)%>/g, "',$1,'")
          .split("\t").join("');")
          .split("%>").join("p.push('")
          .split("\r").join("\\'")
      + "');}return p.join('');");
   
    // Provide some basic currying to the user
    return data ? fn( data ) : fn;
  };
})();
