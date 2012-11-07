/** Spreadsheet **/
(function() {

function getRowLabel(value){
  if (this.options.spreadsheet.tickFormatter){
    //TODO maybe pass the xaxis formatter to the custom tick formatter as an opt-out?
    return this.options.spreadsheet.tickFormatter(value);
  }
  else {
    var t = _.find(this.axes.x.ticks, function(t){return t.v == value;});
    if (t) {
      return t.label;
    }
    return value;
  }
}

var
  D = Flotr.DOM,
  _ = Flotr._;

Flotr.addPlugin('spreadsheet', {
  options: {
    show: false,           // => show the data grid using two tabs
    tabGraphLabel: 'Graph',
    tabDataLabel: 'Data',
    toolbarDownload: 'Download CSV', // @todo: add better language support
    toolbarSelectAll: 'Select all',
    csvFileSeparator: ',',
    decimalSeparator: '.',
    tickFormatter: null,
    initialTab: 'graph'
  },
  /**
   * Builds the tabs in the DOM
   */
  callbacks: {
    'flotr:afterconstruct': function(){
      // @TODO necessary?
      //this.el.select('.flotr-tabs-group,.flotr-datagrid-container').invoke('remove');
      
      if (!this.options.spreadsheet.show) return;
      
      var ss = this.spreadsheet,
        container = D.node('<div class="flotr-tabs-group" style="position:absolute;left:0px;width:'+this.canvasWidth+'px"></div>'),
        graph = D.node('<div style="float:left" class="flotr-tab selected">'+this.options.spreadsheet.tabGraphLabel+'</div>'),
        data = D.node('<div style="float:left" class="flotr-tab">'+this.options.spreadsheet.tabDataLabel+'</div>'),
        offset;

      ss.tabsContainer = container;
      ss.tabs = { graph : graph, data : data };

      D.insert(container, graph);
      D.insert(container, data);
      D.insert(this.el, container);

      offset = D.size(data).height + 2;
      this.plotOffset.bottom += offset;

      D.setStyles(container, {top: this.canvasHeight-offset+'px'});

      this.
        observe(graph, 'click',  function(){ss.showTab('graph');}).
        observe(data, 'click', function(){ss.showTab('data');});
      if (this.options.spreadsheet.initialTab !== 'graph'){
        ss.showTab(this.options.spreadsheet.initialTab);
      }
    }
  },
  /**
   * Builds a matrix of the data to make the correspondance between the x values and the y values :
   * X value => Y values from the axes
   * @return {Array} The data grid
   */
  loadDataGrid: function(){
    if (this.seriesData) return this.seriesData;

    var s = this.series,
        rows = {};

    /* The data grid is a 2 dimensions array. There is a row for each X value.
     * Each row contains the x value and the corresponding y value for each serie ('undefined' if there isn't one)
    **/
    _.each(s, function(serie, i){
      _.each(serie.data, function (v) {
        var x = v[0],
            y = v[1],
            r = rows[x];
        if (r) {
          r[i+1] = y;
        } else {
          var newRow = [];
          newRow[0] = x;
          newRow[i+1] = y;
          rows[x] = newRow;
        }
      });
    });

    // The data grid is sorted by x value
    this.seriesData = _.sortBy(rows, function(row, x){
      return parseInt(x, 10);
    });
    return this.seriesData;
  },
  /**
   * Constructs the data table for the spreadsheet
   * @todo make a spreadsheet manager (Flotr.Spreadsheet)
   * @return {Element} The resulting table element
   */
  constructDataGrid: function(){
    // If the data grid has already been built, nothing to do here
    if (this.spreadsheet.datagrid) return this.spreadsheet.datagrid;
    
    var s = this.series,
        datagrid = this.spreadsheet.loadDataGrid(),
        colgroup = ['<colgroup><col />'],
        buttonDownload, buttonSelect, t;
    
    // First row : series' labels
    var html = ['<table class="flotr-datagrid"><tr class="first-row">'];
    html.push('<th>&nbsp;</th>');
    _.each(s, function(serie,i){
      html.push('<th scope="col">'+(serie.label || String.fromCharCode(65+i))+'</th>');
      colgroup.push('<col />');
    });
    html.push('</tr>');
    // Data rows
    _.each(datagrid, function(row){
      html.push('<tr>');
      _.times(s.length+1, function(i){
        var tag = 'td',
            value = row[i],
            // TODO: do we really want to handle problems with floating point
            // precision here?
            content = (!_.isUndefined(value) ? Math.round(value*100000)/100000 : '');
        if (i === 0) {
          tag = 'th';
          var label = getRowLabel.call(this, content);
          if (label) content = label;
        }

        html.push('<'+tag+(tag=='th'?' scope="row"':'')+'>'+content+'</'+tag+'>');
      }, this);
      html.push('</tr>');
    }, this);
    colgroup.push('</colgroup>');
    t = D.node(html.join(''));

    /**
     * @TODO disabled this
    if (!Flotr.isIE || Flotr.isIE == 9) {
      function handleMouseout(){
        t.select('colgroup col.hover, th.hover').invoke('removeClassName', 'hover');
      }
      function handleMouseover(e){
        var td = e.element(),
          siblings = td.previousSiblings();
        t.select('th[scope=col]')[siblings.length-1].addClassName('hover');
        t.select('colgroup col')[siblings.length].addClassName('hover');
      }
      _.each(t.select('td'), function(td) {
        Flotr.EventAdapter.
          observe(td, 'mouseover', handleMouseover).
          observe(td, 'mouseout', handleMouseout);
      });
    }
    */

    buttonDownload = D.node(
      '<button type="button" class="flotr-datagrid-toolbar-button">' +
      this.options.spreadsheet.toolbarDownload +
      '</button>');

    buttonSelect = D.node(
      '<button type="button" class="flotr-datagrid-toolbar-button">' +
      this.options.spreadsheet.toolbarSelectAll+
      '</button>');

    this.
      observe(buttonDownload, 'click', _.bind(this.spreadsheet.downloadCSV, this)).
      observe(buttonSelect, 'click', _.bind(this.spreadsheet.selectAllData, this));

    var toolbar = D.node('<div class="flotr-datagrid-toolbar"></div>');
    D.insert(toolbar, buttonDownload);
    D.insert(toolbar, buttonSelect);

    var containerHeight =this.canvasHeight - D.size(this.spreadsheet.tabsContainer).height-2,
        container = D.node('<div class="flotr-datagrid-container" style="position:absolute;left:0px;top:0px;width:'+
          this.canvasWidth+'px;height:'+containerHeight+'px;overflow:auto;z-index:10"></div>');

    D.insert(container, toolbar);
    D.insert(container, t);
    D.insert(this.el, container);
    this.spreadsheet.datagrid = t;
    this.spreadsheet.container = container;

    return t;
  },  
  /**
   * Shows the specified tab, by its name
   * @todo make a tab manager (Flotr.Tabs)
   * @param {String} tabName - The tab name
   */
  showTab: function(tabName){
    if (this.spreadsheet.activeTab === tabName){
      return;
    }
    switch(tabName) {
      case 'graph':
        D.hide(this.spreadsheet.container);
        D.removeClass(this.spreadsheet.tabs.data, 'selected');
        D.addClass(this.spreadsheet.tabs.graph, 'selected');
      break;
      case 'data':
        if (!this.spreadsheet.datagrid)
          this.spreadsheet.constructDataGrid();
        D.show(this.spreadsheet.container);
        D.addClass(this.spreadsheet.tabs.data, 'selected');
        D.removeClass(this.spreadsheet.tabs.graph, 'selected');
      break;
      default:
        throw 'Illegal tab name: ' + tabName;
    }
    this.spreadsheet.activeTab = tabName;
  },
  /**
   * Selects the data table in the DOM for copy/paste
   */
  selectAllData: function(){
    if (this.spreadsheet.tabs) {
      var selection, range, doc, win, node = this.spreadsheet.constructDataGrid();

      this.spreadsheet.showTab('data');
      
      // deferred to be able to select the table
      setTimeout(function () {
        if ((doc = node.ownerDocument) && (win = doc.defaultView) && 
            win.getSelection && doc.createRange && 
            (selection = window.getSelection()) && 
            selection.removeAllRanges) {
            range = doc.createRange();
            range.selectNode(node);
            selection.removeAllRanges();
            selection.addRange(range);
        }
        else if (document.body && document.body.createTextRange && 
                (range = document.body.createTextRange())) {
            range.moveToElementText(node);
            range.select();
        }
      }, 0);
      return true;
    }
    else return false;
  },
  /**
   * Converts the data into CSV in order to download a file
   */
  downloadCSV: function(){
    var csv = '',
        series = this.series,
        options = this.options,
        dg = this.spreadsheet.loadDataGrid(),
        separator = encodeURIComponent(options.spreadsheet.csvFileSeparator);
    
    if (options.spreadsheet.decimalSeparator === options.spreadsheet.csvFileSeparator) {
      throw "The decimal separator is the same as the column separator ("+options.spreadsheet.decimalSeparator+")";
    }
    
    // The first row
    _.each(series, function(serie, i){
      csv += separator+'"'+(serie.label || String.fromCharCode(65+i)).replace(/\"/g, '\\"')+'"';
    });

    csv += "%0D%0A"; // \r\n
    
    // For each row
    csv += _.reduce(dg, function(memo, row){
      var rowLabel = getRowLabel.call(this, row[0]) || '';
      rowLabel = '"'+(rowLabel+'').replace(/\"/g, '\\"')+'"';
      var numbers = row.slice(1).join(separator);
      if (options.spreadsheet.decimalSeparator !== '.') {
        numbers = numbers.replace(/\./g, options.spreadsheet.decimalSeparator);
      }
      return memo + rowLabel+separator+numbers+"%0D%0A"; // \t and \r\n
    }, '', this);

    if (Flotr.isIE && Flotr.isIE < 9) {
      csv = csv.replace(new RegExp(separator, 'g'), decodeURIComponent(separator)).replace(/%0A/g, '\n').replace(/%0D/g, '\r');
      window.open().document.write(csv);
    }
    else window.open('data:text/csv,'+csv);
  }
});
})();
