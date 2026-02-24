/*
  Copyright (c) 2009 Open Lab
  Written by Roberto Bicchierai http://roberto.open-lab.com
  Permission is hereby granted, free of charge, to any person obtaining
  a copy of this software and associated documentation files (the
  "Software"), to deal in the Software without restriction, including
  without limitation the rights to use, copy, modify, merge, publish,
  distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so, subject to
  the following conditions:

  The above copyright notice and this permission notice shall be
  included in all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
  LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

jQuery.fn.dateField = function(options) {
  //console.debug("dateField",options);
  //check if the input field is passed correctly
  if (!options.inputField){
    console.error("You must supply an input field");
    return false;
  }

  // --------------------------  start default option values --------------------------

  if (typeof(options.firstDayOfWeek) == "undefined")
    options.firstDayOfWeek=Date.firstDayOfWeek;

  if (typeof(options.useWheel) == "undefined")
    options.useWheel=true;

  if (typeof(options.dateFormat) == "undefined")
    options.dateFormat=Date.defaultFormat;

  if (typeof(options.todayLabel) == "undefined")
    options.todayLabel=Date.today;

  /* optional
    options.notBeforeMillis //disable buttons if before millis
    options.notAfterMillis //disable buttons if after millis
    options.width // imposta una larghezza al calendario
    options.height
    options.showToday // show "today" on the year or month bar
    options.centerOnScreen //se true centra invece che usa nearBestPosition
    options.useYears:0 // se >0 non disegna prev-next ma n anni prima e n anni dopo quello corrente
    options.useMonths:0 // se >0 non disegna prev-next ma n mesi prima e n mesi dopo quello corrente
  */
  // --------------------------  end default option values --------------------------



  // ------------------ start
  if(options.inputField.is("[readonly]") && !options.inputField.is(".noFocus")  || options.inputField.is("[disabled]"))
    return;

  var calendar = {currentDate: new Date()};
  calendar.options = options;

  //build the calendar on the first element in the set of matched elements.
  var theOpener = this.eq(0);
  var theDiv=$("<div>").addClass("calBox");

  if(options.width)
    theDiv.css("width",options.width);

  if(options.height)
    theDiv.css("height",options.height);


  //create calendar elements elements
  var divNavBar = $("<div>").addClass("calNav");
  var divDays = $("<div>").addClass("calDay");

  divDays.addClass("calFullMonth");
  theDiv.append(divNavBar).append(divDays);

  if (options.isSearchField){
    var divShortcuts=$("<div>").addClass("shortCuts").html("<span title='last quarter'>LQ</span> <span title='last month'>LM</span> <span title='this month'>M</span> <span title='last week'>LW</span> <span title='this week'>W</span> <span title='yesterday'>Y</span> <span title='today'>T</span><span title='tomorrow'>TO</span><span title='next week'>NW</span> <span title='next month'>NM</span> <span title='this quarter'>Q</span> <span title='next quarter'>NQ</span>");
    divShortcuts.click(function(ev){
      var el=$(ev.target);
      if(el.is("span")){
        if (!options.isSearchField)
          options.inputField.val(Date.parseString(el.text().trim(),options.dateFormat,true).format(options.dateFormat));
        else
          options.inputField.val(el.text().trim());
        calendar.closeCalendar()
      }
    });
    theDiv.append(divShortcuts);
  }

  //mobile management
  if ($("body").is(".mobile")){
    enableComponentOverlay(options.inputField,theDiv);
  }
  $("body").append(theDiv);


  if (options.centerOnScreen){
    theDiv.oneTime(10,"ce",function(){$(this).centerOnScreen()});
  } else {
    nearBestPosition(theOpener,theDiv);
  }
  theDiv.css("z-index",10000);


  //register for click outside. Delayed to avoid it run immediately
  $("body").oneTime(100, "regclibodcal", function() {
    $("body").bind("click.dateField", function() {
      calendar.closeCalendar();
    });
  });


  calendar.drawCalendar = function(date) {
    calendar.currentDate = date;
    //console.debug("drawCalendar",date);


    var fillNavBar = function(date) {
      //console.debug("fillNavBar",date);
      var today = new Date();//today
      divNavBar.empty();

      var showToday = options.showToday;
      //use the classic prev next bar
      if (!options.useYears && !options.useMonths) {
        var t = new Date(date.getTime());
        t.setDate(1);
        t.setMonth(t.getMonth() - 1);
        var spanPrev = $("<span>").addClass("calElement noCallback prev").attr("millis", t.getTime());
        var spanToday = $("<span>").addClass("calElement noCallback goToday").attr("millis", new Date().getTime()).attr("title", "today");
        t.setMonth(t.getMonth() + 1);
        var spanMonth = $("<span>").html(t.format("MMMM yyyy"));
        t.setMonth(t.getMonth() + 1);
        var spanNext = $("<span>").addClass("calElement noCallback next").attr("millis", t.getTime());
        divNavBar.append(spanPrev, spanToday, spanMonth, spanNext);

      // use the year month bar
      } else {
        if (options.useYears>0){
          options.useMonths=options.useMonths||1; //if shows years -> shows also months
          t = new Date(date.getTime());
          var yB= $("<div class='calYear'>");
          var w=100/(2*options.useYears+1+(showToday?1:0));
          t.setFullYear(t.getFullYear()-options.useYears);
          if(showToday){
            var s = $("<span>").addClass("calElement noCallback goToday").attr("millis", today.getTime()).append(options.todayLabel).css("width",w+"%");
            showToday=false;
            yB.append(s);
          }
          for (var i=-options.useYears;i<=options.useYears;i++){
            var s = $("<span>").addClass("calElement noCallback").attr("millis", t.getTime()).append(t.getFullYear()).css("width",w+"%");
            if (today.getFullYear()== t.getFullYear()) //current year
              s.addClass("today");
            if (i==0) //selected year
              s.addClass("selected");

            yB.append(s);
            t.setFullYear(t.getFullYear()+1);
          }
          divNavBar.append(yB);
        }
        if (options.useMonths>0){
          t = new Date(date.getTime());
          t.setDate(1);
          var w=100/(2*options.useMonths+1+(showToday?1:0));
          t.setMonth(t.getMonth()-options.useMonths);
          var yB= $("<div class='calMonth'>");

          if(showToday){
            var s = $("<span>").addClass("calElement noCallback goToday").attr("millis", today.getTime()).append(options.todayLabel).css("width",w+"%");
            yB.append(s);
          }

          for (var i=-options.useMonths;i<=options.useMonths;i++){
            var s = $("<span>").addClass("calElement noCallback").attr("millis", t.getTime()).append(t.format("MMM")).css("width",w+"%");
            if (today.getFullYear()== t.getFullYear() && today.getMonth()== t.getMonth()) //current year
              s.addClass("today");
            if (i==0) //selected month
              s.addClass("selected");
            yB.append(s);
            t.setMonth(t.getMonth()+1);
          }
          divNavBar.append(yB);
        }
      }

    };

    var fillDaysFullMonth = function(date) {
      divDays.empty();
      var today = new Date();//today
      var w = 100/7;
      // draw day headers
      var d = new Date(date);
      d.setFirstDayOfThisWeek(options.firstDayOfWeek);
      for (var i = 0; i < 7; i++) {
        var span = $("<span>").addClass("calDayHeader").attr("day", d.getDay());
        if (d.isHoliday())
          span.addClass("holy");
        span.css("width",w+"%");
        span.html(Date.dayAbbreviations[d.getDay()]);

        //call the dayHeaderRenderer
        if (typeof(options.dayHeaderRenderer) == "function")
          options.dayHeaderRenderer(span,d.getDay());

        divDays.append(span);
        d.setDate(d.getDate()+1);
      }

      //draw cells
      d = new Date(date);
      d.setDate(1); // set day to start of month
      d.setFirstDayOfThisWeek(options.firstDayOfWeek);//go to first day of week

      var i=0;

      while ((d.getMonth()<=date.getMonth() && d.getFullYear()<=date.getFullYear()) || d.getFullYear()<date.getFullYear() || (i%7!=0)) {
        var span = $("<span>").addClass("calElement day").attr("millis", d.getTime());

        span.html("<span class=dayNumber>" + d.getDate() + "</span>").css("width",w+"%");
        if (d.getYear() == today.getYear() && d.getMonth() == today.getMonth() && d.getDate() == today.getDate())
          span.addClass("today");
        if (d.getYear() == date.getYear() && d.getMonth() == date.getMonth() && d.getDate() == date.getDate())
          span.addClass("selected");

        if (d.isHoliday())
          span.addClass("holy");

        if(d.getMonth()!=date.getMonth())
          span.addClass("calOutOfScope");

        //call the dayRenderer
        if (typeof(options.dayRenderer) == "function")
          options.dayRenderer(span,d);

        divDays.append(span);
        d.setDate(d.getDate()+1);
        i++;
      }

    };

    fillNavBar(date);
    fillDaysFullMonth(date);

    //disable all buttons out of validity period
    if (options.notBeforeMillis ||options.notAfterMillis) {
      var notBefore = options.notBeforeMillis ? options.notBeforeMillis : Number.MIN_VALUE;
      var notAfter = options.notAfterMillis ? options.notAfterMillis : Number.MAX_VALUE;
      divDays.find(".calElement[millis]").each(function(){
        var el=$(this);
        var m=parseInt(el.attr("millis"));
        if (m>notAfter || m<notBefore)
          el.addClass("disabled");
      })
    }

  };

  calendar.closeCalendar=function(){
    //mobile management
    if ($("body").is(".mobile")){
      disableComponentOverlay();
    }
    theDiv.remove();
    $("body").unbind("click.dateField");
  };

  theDiv.click(function(ev) {
    var el = $(ev.target).closest(".calElement");
    if (el.length > 0) {
      var millis = parseInt(el.attr("millis"));
      var date = new Date(millis);

      if (el.is(".disabled")) {
        ev.stopPropagation();
        return;
      }

      if (el.hasClass("day")) {
        calendar.closeCalendar();
        if (!el.is(".noCallback")) {
          options.inputField.val(date.format(options.dateFormat)).attr("millis", date.getTime()).focus();
          if (typeof(options.callback) == "function")
            options.callback.apply(options.inputField,[date]); // in callBack you can use "this" that refers to the input
        }
      } else {
        calendar.drawCalendar(date);
      }
    }
    ev.stopPropagation();
  });


  //if mousewheel
  if ($.event.special.mousewheel && options.useWheel) {
    divDays.mousewheel(function(event, delta) {
      var d = new Date(calendar.currentDate.getTime());
      d.setMonth(d.getMonth() + delta);
      calendar.drawCalendar(d);
      return false;
    });
  }


  // start calendar to the date in the input
  var dateStr=options.inputField.val();

  if (!dateStr || !Date.isValid(dateStr,options.dateFormat,true)){
    calendar.drawCalendar(new Date());
  } else {
    var date = Date.parseString(dateStr,options.dateFormat,true);
    var newDateStr=date.format(options.dateFormat);
    //set date string formatted if not equals
    if (!options.isSearchField) {
      options.inputField.attr("millis", date.getTime());
      if (dateStr != newDateStr)
        options.inputField.val(newDateStr);
    }
    calendar.drawCalendar(date);
  }

  return calendar;
};
