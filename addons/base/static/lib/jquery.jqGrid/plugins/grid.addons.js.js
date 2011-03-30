(function($){
/*
 * jqGrid methods without support. Use as you wish
 * Tony Tomov tony@trirand.com
 * http://trirand.com/blog/
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl-2.0.html
 *
 * This list of deprecated methods.
 * If you instead want to use them, please include this file after the grid main file.
 * Some methods will be then overwritten.
 *
 */
/*global jQuery, $ */

$.jgrid.extend({
// This is the ols search Filter method used in navigator.
	searchGrid : function (p) {
		p = $.extend({
			recreateFilter: false,
			drag: true,
			sField:'searchField',
			sValue:'searchString',
			sOper: 'searchOper',
			sFilter: 'filters',
            loadDefaults: true, // this options activates loading of default filters from grid's postData for Multipe Search only.
			beforeShowSearch: null,
			afterShowSearch : null,
			onInitializeSearch: null,
			closeAfterSearch : false,
			closeAfterReset: false,
			closeOnEscape : false,
			multipleSearch : false,
			cloneSearchRowOnAdd: true,
			// translation
			// if you want to change or remove the order change it in sopt
			// ['bw','eq','ne','lt','le','gt','ge','ew','cn']
			sopt: null,
			// Note: stringResult is intentionally declared "undefined by default".
			//  you are velcome to define stringResult expressly in the options you pass to searchGrid()
			//  stringResult is a "safeguard" measure to insure we post sensible data when communicated as form-encoded
			//  see http://github.com/tonytomov/jqGrid/issues/#issue/36
			//
			//  If this value is not expressly defined in the incoming options,
			// lower in the code we will infer the value based on value of multipleSearch
			stringResult: undefined,
			onClose : null,
			// useDataProxy allows ADD, EDIT and DEL code to bypass calling $.ajax
			// directly when grid's 'dataProxy' property (grid.p.dataProxy) is a function.
			// Used for "editGridRow" and "delGridRow" below and automatically flipped to TRUE
			// when ajax setting's 'url' (grid's 'editurl') property is undefined.
			// When 'useDataProxy' is true, instead of calling $.ajax.call(gridDOMobj, o, i) we call
			// gridDOMobj.p.dataProxy.call(gridDOMobj, o, i)
			//
			// Behavior is extremely similar to when 'datatype' is a function, but arguments are slightly different.
			// Normally the following is fed to datatype.call(a, b, c):
			//   a = Pointer to grid's table DOM element, b = grid.p.postdata, c = "load_"+grid's ID
			// In cases of "edit" and "del" the following is fed:
			//   a = Pointer to grid's table DOM element (same),
			//   b = extended Ajax Options including postdata in "data" property. (different object type)
			//   c = "set_"+grid's ID in case of "edit" and "del_"+grid's ID in case of "del" (same type, different content)
			// The major difference is that complete ajax options object, with attached "complete" and "error"
			// callback functions is fed instead of only post data.
			// This allows you to emulate a $.ajax call (including calling "complete"/"error"),
			// while retrieving the data locally in the browser.
			useDataProxy: false,
			overlay : true
		}, $.jgrid.search, p || {});
		return this.each(function() {
			var $t = this;
			if(!$t.grid) {return;}
			var fid = "fbox_"+$t.p.id,
			showFrm = true;
            function applyDefaultFilters(gridDOMobj, filterSettings) {
				/*
                gridDOMobj = ointer to grid DOM object ( $(#list)[0] )
                What we need from gridDOMobj:
                gridDOMobj.SearchFilter is the pointer to the Search box, once it's created.
                gridDOMobj.p.postData - dictionary of post settings. These can be overriden at grid creation to
                contain default filter settings. We will parse these and will populate the search with defaults.
                filterSettings - same settings object you (would) pass to $().jqGrid('searchGrid', filterSettings);
                */

                // Pulling default filter settings out of postData property of grid's properties.:
                var defaultFilters = gridDOMobj.p.postData[filterSettings.sFilter];
                // example of what we might get: {"groupOp":"and","rules":[{"field":"amount","op":"eq","data":"100"}]}
				// suppose we have imported this with grid import, the this is a string.
				if(typeof(defaultFilters) == "string") {
					defaultFilters = $.jgrid.parse(defaultFilters);
				}
                if (defaultFilters) {
                    if (defaultFilters.groupOp) {
                        gridDOMobj.SearchFilter.setGroupOp(defaultFilters.groupOp);
                    }
                    if (defaultFilters.rules) {
                        var f, i = 0, li = defaultFilters.rules.length, success = false;
                        for (; i < li; i++) {
                            f = defaultFilters.rules[i];
                            // we are not trying to counter all issues with filter declaration here. Just the basics to avoid lookup exceptions.
                            if (f.field !== undefined && f.op !== undefined && f.data !== undefined) {
                                success = gridDOMobj.SearchFilter.setFilter({
                                    'sfref':gridDOMobj.SearchFilter.$.find(".sf:last"),
                                    'filter':$.extend({},f)
                                });
								if (success) { gridDOMobj.SearchFilter.add(); }
                            }
                        }
                    }
				}
            } // end of applyDefaultFilters
			function hideFilter(selector) {
				if(p.onClose){
					var fclm = p.onClose(selector);
					if(typeof fclm == 'boolean' && !fclm) { return; }
				}
				selector.hide();
				if(p.overlay === true) {
					$(".jqgrid-overlay:first","#gbox_"+$t.p.id).hide();
				}
			}
			function showFilter(){
				var fl = $(".ui-searchFilter").length;
				if(fl > 1) {
					var zI = $("#"+fid).css("zIndex");
					$("#"+fid).css({zIndex:parseInt(zI,10)+fl});
				}
				$("#"+fid).show();
				if(p.overlay === true) {
					$(".jqgrid-overlay:first","#gbox_"+$t.p.id).show();
				}
				try{$(':input:visible',"#"+fid)[0].focus();}catch(_){}
			}
			function searchFilters(filters) {
				var hasFilters = (filters !== undefined),
				grid = $("#"+$t.p.id),
				sdata={};
				if(p.multipleSearch===false) {
					sdata[p.sField] = filters.rules[0].field;
					sdata[p.sValue] = filters.rules[0].data;
					sdata[p.sOper] = filters.rules[0].op;
					if(sdata.hasOwnProperty(p.sFilter) ) {
						delete sdata[p.sFilter];
					}
				} else {
					sdata[p.sFilter] = filters;
					$.each([p.sField, p.sValue, p.sOper], function(i, n){
						if(sdata.hasOwnProperty(n)) { delete sdata[n];}
					});
				}
				grid[0].p.search = hasFilters;
				$.extend(grid[0].p.postData,sdata);
				grid.trigger("reloadGrid",[{page:1}]);
				if(p.closeAfterSearch) { hideFilter($("#"+fid)); }
			}
			function resetFilters(op) {
				var reload = op && op.hasOwnProperty("reload") ? op.reload : true,
				grid = $("#"+$t.p.id),
				sdata={};
				grid[0].p.search = false;
				if(p.multipleSearch===false) {
					sdata[p.sField] = sdata[p.sValue] = sdata[p.sOper] = "";
				} else {
					sdata[p.sFilter] = "";
				}
				$.extend(grid[0].p.postData,sdata);
				if(reload) {
					grid.trigger("reloadGrid",[{page:1}]);
				}
				if(p.closeAfterReset) { hideFilter($("#"+fid)); }
			}
			if($.fn.searchFilter) {
				if(p.recreateFilter===true) {$("#"+fid).remove();}
				if( $("#"+fid).html() !== null ) {
					if ( $.isFunction(p.beforeShowSearch) ) {
						showFrm = p.beforeShowSearch($("#"+fid));
						if(typeof(showFrm) == "undefined") {
							showFrm = true;
						}
					}
					if(showFrm === false) { return; }
					showFilter();
					if( $.isFunction(p.afterShowSearch) ) { p.afterShowSearch($("#"+fid)); }
				} else {
					var fields = [],
					colNames = $("#"+$t.p.id).jqGrid("getGridParam","colNames"),
					colModel = $("#"+$t.p.id).jqGrid("getGridParam","colModel"),
					stempl = ['eq','ne','lt','le','gt','ge','bw','bn','in','ni','ew','en','cn','nc'],
					j,pos,k,oprtr=[];
					if (p.sopt !==null) {
						k=0;
						for(j=0;j<p.sopt.length;j++) {
							if( (pos= $.inArray(p.sopt[j],stempl)) != -1 ){
								oprtr[k] = {op:p.sopt[j],text: p.odata[pos]};
								k++;
							}
						}
					} else {
						for(j=0;j<stempl.length;j++) {
							oprtr[j] = {op:stempl[j],text: p.odata[j]};
						}
					}
				    $.each(colModel, function(i, v) {
				        var searchable = (typeof v.search === 'undefined') ?  true: v.search ,
				        hidden = (v.hidden === true),
						soptions = $.extend({}, {text: colNames[i], itemval: v.index || v.name}, this.searchoptions),
						ignoreHiding = (soptions.searchhidden === true);
						if(typeof soptions.sopt !== 'undefined') {
							k=0;
							soptions.ops =[];
							if(soptions.sopt.length>0) {
								for(j=0;j<soptions.sopt.length;j++) {
									if( (pos= $.inArray(soptions.sopt[j],stempl)) != -1 ){
										soptions.ops[k] = {op:soptions.sopt[j],text: p.odata[pos]};
										k++;
									}
								}
							}
						}
						if(typeof(this.stype) === 'undefined') { this.stype='text'; }
						if(this.stype == 'select') {
							if ( soptions.dataUrl !== undefined) {}
							else {
								var eov;
								if(soptions.value) {
									eov = soptions.value;
								} else if(this.editoptions) {
									eov = this.editoptions.value;
								}
								if(eov) {
									soptions.dataValues =[];
									if(typeof(eov) === 'string') {
										var so = eov.split(";"),sv;
										for(j=0;j<so.length;j++) {
											sv = so[j].split(":");
											soptions.dataValues[j] ={value:sv[0],text:sv[1]};
										}
									} else if (typeof(eov) === 'object') {
										j=0;
										for (var key in eov) {
											if(eov.hasOwnProperty(key)) {
												soptions.dataValues[j] ={value:key,text:eov[key]};
												j++;
											}
										}
									}
								}
							}
						}
				        if ((ignoreHiding && searchable) || (searchable && !hidden)) {
							fields.push(soptions);
						}
					});
					if(fields.length>0){
						$("<div id='"+fid+"' role='dialog' tabindex='-1'></div>").insertBefore("#gview_"+$t.p.id);
						// Before we create searchFilter we need to decide if we want to get back a string or a JS object.
						//  see http://github.com/tonytomov/jqGrid/issues/#issue/36 for background on the issue.
						// If p.stringResult is defined, it was explisitly passed to us by user. Honor the choice, whatever it is.
						if (p.stringResult===undefined) {
							// to provide backward compatibility, inferring stringResult value from multipleSearch
							p.stringResult = p.multipleSearch;
						}
						// we preserve the return value here to retain access to .add() and other good methods of search form.
						$t.SearchFilter = $("#"+fid).searchFilter(fields, { groupOps: p.groupOps, operators: oprtr, onClose:hideFilter, resetText: p.Reset, searchText: p.Find, windowTitle: p.caption,  rulesText:p.rulesText, matchText:p.matchText, onSearch: searchFilters, onReset: resetFilters,stringResult:p.stringResult, ajaxSelectOptions: $.extend({},$.jgrid.ajaxOptions,$t.p.ajaxSelectOptions ||{}), clone: p.cloneSearchRowOnAdd });
						$(".ui-widget-overlay","#"+fid).remove();
						if($t.p.direction=="rtl") { $(".ui-closer","#"+fid).css("float","left"); }
						if (p.drag===true) {
							$("#"+fid+" table thead tr:first td:first").css('cursor','move');
							if(jQuery.fn.jqDrag) {
								$("#"+fid).jqDrag($("#"+fid+" table thead tr:first td:first"));
							} else {
								try {
									$("#"+fid).draggable({handle: $("#"+fid+" table thead tr:first td:first")});
								} catch (e) {}
							}
						}
						if(p.multipleSearch === false) {
							$(".ui-del, .ui-add, .ui-del, .ui-add-last, .matchText, .rulesText", "#"+fid).hide();
							$("select[name='groupOp']","#"+fid).hide();
						}
                        if (p.multipleSearch === true && p.loadDefaults === true) {
                            applyDefaultFilters($t, p);
                        }
						if ( $.isFunction(p.onInitializeSearch) ) { p.onInitializeSearch( $("#"+fid) ); }
						if ( $.isFunction(p.beforeShowSearch) ) {
							showFrm = p.beforeShowSearch($("#"+fid));
							if(typeof(showFrm) == "undefined") {
								showFrm = true;
							}
						}
						if(showFrm === false) { return; }
						showFilter();
						if( $.isFunction(p.afterShowSearch) ) { p.afterShowSearch($("#"+fid)); }
						if(p.closeOnEscape===true){
							$("#"+fid).keydown( function( e ) {
								if( e.which == 27 ) {
									hideFilter($("#"+fid));
								}
								if (e.which == 13) {
									$(".ui-search", this).click();
								}
							});
						}
					}
				}
			}
		});
	},
	// methods taken from grid.custom.
	updateGridRows : function (data, rowidname, jsonreader) {
		var nm, success=false, title;
		this.each(function(){
			var t = this, vl, ind, srow, sid;
			if(!t.grid) {return false;}
			if(!rowidname) { rowidname = "id"; }
			if( data  && data.length >0 ) {
				$(data).each(function(j){
					srow = this;
					ind = t.rows.namedItem(srow[rowidname]);
					if(ind) {
						sid = srow[rowidname];
						if(jsonreader === true){
							if(t.p.jsonReader.repeatitems === true) {
								if(t.p.jsonReader.cell) {srow = srow[t.p.jsonReader.cell];}
								for (var k=0;k<srow.length;k++) {
									vl = t.formatter( sid, srow[k], k, srow, 'edit');
									title = t.p.colModel[k].title ? {"title":$.jgrid.stripHtml(vl)} : {};
									if(t.p.treeGrid===true && nm == t.p.ExpandColumn) {
										$("td:eq("+k+") > span:first",ind).html(vl).attr(title);
									} else {
										$("td:eq("+k+")",ind).html(vl).attr(title);
									}
								}
								success = true;
								return true;
							}
						}
						$(t.p.colModel).each(function(i){
							nm = jsonreader===true ? this.jsonmap || this.name :this.name;
							if( srow[nm] !== undefined) {
								vl = t.formatter( sid, srow[nm], i, srow, 'edit');
								title = this.title ? {"title":$.jgrid.stripHtml(vl)} : {};
								if(t.p.treeGrid===true && nm == t.p.ExpandColumn) {
									$("td:eq("+i+") > span:first",ind).html(vl).attr(title);
								} else {
									$("td:eq("+i+")",ind).html(vl).attr(title);
								}
								success = true;
							}
						});
					}
				});
			}
		});
		return success;
	},
	// Form search - sorry for this method. Instead use ne jqFilter method.
	filterGrid : function(gridid,p){
		p = $.extend({
			gridModel : false,
			gridNames : false,
			gridToolbar : false,
			filterModel: [], // label/name/stype/defval/surl/sopt
			formtype : "horizontal", // horizontal/vertical
			autosearch: true, // if set to false a serch button should be enabled.
			formclass: "filterform",
			tableclass: "filtertable",
			buttonclass: "filterbutton",
			searchButton: "Search",
			clearButton: "Clear",
			enableSearch : false,
			enableClear: false,
			beforeSearch: null,
			afterSearch: null,
			beforeClear: null,
			afterClear: null,
			url : '',
			marksearched: true
		},p  || {});
		return this.each(function(){
			var self = this;
			this.p = p;
			if(this.p.filterModel.length === 0 && this.p.gridModel===false) { alert("No filter is set"); return;}
			if( !gridid) {alert("No target grid is set!"); return;}
			this.p.gridid = gridid.indexOf("#") != -1 ? gridid : "#"+gridid;
			var gcolMod = $(this.p.gridid).jqGrid("getGridParam",'colModel');
			if(gcolMod) {
				if( this.p.gridModel === true) {
					var thegrid = $(this.p.gridid)[0];
					var sh;
					// we should use the options search, edittype, editoptions
					// additionally surl and defval can be added in grid colModel
					$.each(gcolMod, function (i,n) {
						var tmpFil = [];
						this.search = this.search === false ? false : true;
						if(this.editrules && this.editrules.searchhidden === true) {
							sh = true;
						} else {
							if(this.hidden === true ) {
								sh = false;
							} else {
								sh = true;
							}
						}
						if( this.search === true && sh === true) {
							if(self.p.gridNames===true) {
								tmpFil.label = thegrid.p.colNames[i];
							} else {
								tmpFil.label = '';
							}
							tmpFil.name = this.name;
							tmpFil.index = this.index || this.name;
							// we support only text and selects, so all other to text
							tmpFil.stype = this.edittype || 'text';
							if(tmpFil.stype != 'select' ) {
								tmpFil.stype = 'text';
							}
							tmpFil.defval = this.defval || '';
							tmpFil.surl = this.surl || '';
							tmpFil.sopt = this.editoptions || {};
							tmpFil.width = this.width;
							self.p.filterModel.push(tmpFil);
						}
					});
				} else {
					$.each(self.p.filterModel,function(i,n) {
						for(var j=0;j<gcolMod.length;j++) {
							if(this.name == gcolMod[j].name) {
								this.index = gcolMod[j].index || this.name;
								break;
							}
						}
						if(!this.index) {
							this.index = this.name;
						}
					});
				}
			} else {
				alert("Could not get grid colModel"); return;
			}
			var triggerSearch = function() {
				var sdata={}, j=0, v;
				var gr = $(self.p.gridid)[0], nm;
                gr.p.searchdata = {};
				if($.isFunction(self.p.beforeSearch)){self.p.beforeSearch();}
				$.each(self.p.filterModel,function(i,n){
                    nm = this.index;
					if(this.stype === 'select') {
						v = $("select[name="+nm+"]",self).val();
						if(v) {
							sdata[nm] = v;
							if(self.p.marksearched){
								$("#jqgh_"+this.name,gr.grid.hDiv).addClass("dirty-cell");
							}
							j++;
						} else {
							if(self.p.marksearched){
								$("#jqgh_"+this.name,gr.grid.hDiv).removeClass("dirty-cell");
							}
                               try {
                                   delete gr.p.postData[this.index];
                               } catch (e) {}
						}
					} else {
						v = $("input[name="+nm+"]",self).val();
						if(v) {
							sdata[nm] = v;
							if(self.p.marksearched){
								$("#jqgh_"+this.name,gr.grid.hDiv).addClass("dirty-cell");
							}
							j++;
						} else {
							if(self.p.marksearched){
								$("#jqgh_"+this.name,gr.grid.hDiv).removeClass("dirty-cell");
							}
								try {
									delete gr.p.postData[this.index];
                            } catch(x) {}
						}
					}
				});
				var sd =  j>0 ? true : false;
                $.extend(gr.p.postData,sdata);
				var saveurl;
				if(self.p.url) {
					saveurl = $(gr).jqGrid("getGridParam",'url');
					$(gr).jqGrid("setGridParam",{url:self.p.url});
				}
			    $(gr).jqGrid("setGridParam",{search:sd}).trigger("reloadGrid",[{page:1}]);
				if(saveurl) {$(gr).jqGrid("setGridParam",{url:saveurl});}
				if($.isFunction(self.p.afterSearch)){self.p.afterSearch();}
			};
			var clearSearch = function(){
				var sdata={}, v, j=0;
				var gr = $(self.p.gridid)[0], nm;
				if($.isFunction(self.p.beforeClear)){self.p.beforeClear();}
				$.each(self.p.filterModel,function(i,n){
                    nm = this.index;
					v = (this.defval) ? this.defval : "";
					if(!this.stype){this.stype='text';}
					switch (this.stype) {
						case 'select' :
							var v1;
							$("select[name="+nm+"] option",self).each(function (i){
                                if(i===0) { this.selected = true; }
								if ($(this).text() == v) {
									this.selected = true;
									v1 = $(this).val();
									return false;
								}
							});
							if(v1) {
								// post the key and not the text
								sdata[nm] = v1;
								if(self.p.marksearched){
									$("#jqgh_"+this.name,gr.grid.hDiv).addClass("dirty-cell");
								}
								j++;
							} else {
								if(self.p.marksearched){
									$("#jqgh_"+this.name,gr.grid.hDiv).removeClass("dirty-cell");
								}
                                try {
                                    delete gr.p.postData[this.index];
                                } catch (e) {}
							}
							break;
						case 'text':
							$("input[name="+nm+"]",self).val(v);
							if(v) {
								sdata[nm] = v;
								if(self.p.marksearched){
									$("#jqgh_"+this.name,gr.grid.hDiv).addClass("dirty-cell");
								}
								j++;
							} else {
								if(self.p.marksearched){
									$("#jqgh_"+this.name,gr.grid.hDiv).removeClass("dirty-cell");
								}
                                try {
                                    delete gr.p.postData[this.index];
                                } catch (k) {}
							}
                            break;
					}
				});
				var sd =  j>0 ? true : false;
                $.extend(gr.p.postData,sdata);
				var saveurl;
				if(self.p.url) {
					saveurl = $(gr).jqGrid("getGridParam",'url');
					$(gr).jqGrid("setGridParam",{url:self.p.url});
				}
				$(gr).jqGrid("setGridParam",{search:sd}).trigger("reloadGrid",[{page:1}]);
				if(saveurl) {$(gr).jqGrid("setGridParam",{url:saveurl});}
				if($.isFunction(self.p.afterClear)){self.p.afterClear();}
			};
			var tbl;
			var formFill = function(){
				var tr = document.createElement("tr");
				var tr1, sb, cb,tl,td;
				if(self.p.formtype=='horizontal'){
					$(tbl).append(tr);
				}
				$.each(self.p.filterModel,function(i,n){
					tl = document.createElement("td");
					$(tl).append("<label for='"+this.name+"'>"+this.label+"</label>");
					td = document.createElement("td");
					var $t=this;
					if(!this.stype) { this.stype='text';}
					switch (this.stype)
					{
					case "select":
						if(this.surl) {
							// data returned should have already constructed html select
							$(td).load(this.surl,function(){
								if($t.defval) { $("select",this).val($t.defval); }
								$("select",this).attr({name:$t.index || $t.name, id: "sg_"+$t.name});
								if($t.sopt) { $("select",this).attr($t.sopt); }
								if(self.p.gridToolbar===true && $t.width) {
									$("select",this).width($t.width);
								}
								if(self.p.autosearch===true){
									$("select",this).change(function(e){
										triggerSearch();
										return false;
									});
								}
							});
						} else {
							// sopt to construct the values
							if($t.sopt.value) {
								var oSv = $t.sopt.value;
								var elem = document.createElement("select");
								$(elem).attr({name:$t.index || $t.name, id: "sg_"+$t.name}).attr($t.sopt);
								var so, sv, ov;
								if(typeof oSv === "string") {
									so = oSv.split(";");
									for(var k=0; k<so.length;k++){
										sv = so[k].split(":");
										ov = document.createElement("option");
										ov.value = sv[0]; ov.innerHTML = sv[1];
										if (sv[1]==$t.defval) { ov.selected ="selected"; }
										elem.appendChild(ov);
									}
								} else if(typeof oSv === "object" ) {
									for ( var key in oSv) {
										if(oSv.hasOwnProperty(key)) {
											i++;
											ov = document.createElement("option");
											ov.value = key; ov.innerHTML = oSv[key];
											if (oSv[key]==$t.defval) { ov.selected ="selected"; }
											elem.appendChild(ov);
										}
									}
								}
								if(self.p.gridToolbar===true && $t.width) {
									$(elem).width($t.width);
								}
								$(td).append(elem);
								if(self.p.autosearch===true){
									$(elem).change(function(e){
										triggerSearch();
										return false;
									});
								}
							}
						}
						break;
					case 'text':
						var df = this.defval ? this.defval: "";
						$(td).append("<input type='text' name='"+(this.index || this.name)+"' id='sg_"+this.name+"' value='"+df+"'/>");
						if($t.sopt) { $("input",td).attr($t.sopt); }
						if(self.p.gridToolbar===true && $t.width) {
							if($.browser.msie) {
								$("input",td).width($t.width-4);
							} else {
								$("input",td).width($t.width-2);
							}
						}
						if(self.p.autosearch===true){
							$("input",td).keypress(function(e){
								var key = e.charCode ? e.charCode : e.keyCode ? e.keyCode : 0;
								if(key == 13){
									triggerSearch();
									return false;
								}
								return this;
							});
						}
						break;
					}
					if(self.p.formtype=='horizontal'){
						if(self.p.gridToolbar===true && self.p.gridNames===false) {
							$(tr).append(td);
						} else {
							$(tr).append(tl).append(td);
						}
						$(tr).append(td);
					} else {
						tr1 = document.createElement("tr");
						$(tr1).append(tl).append(td);
						$(tbl).append(tr1);
					}
				});
				td = document.createElement("td");
				if(self.p.enableSearch === true){
					sb = "<input type='button' id='sButton' class='"+self.p.buttonclass+"' value='"+self.p.searchButton+"'/>";
					$(td).append(sb);
					$("input#sButton",td).click(function(){
						triggerSearch();
						return false;
					});
				}
				if(self.p.enableClear === true) {
					cb = "<input type='button' id='cButton' class='"+self.p.buttonclass+"' value='"+self.p.clearButton+"'/>";
					$(td).append(cb);
					$("input#cButton",td).click(function(){
						clearSearch();
						return false;
					});
				}
				if(self.p.enableClear === true || self.p.enableSearch === true) {
					if(self.p.formtype=='horizontal') {
						$(tr).append(td);
					} else {
						tr1 = document.createElement("tr");
						$(tr1).append("<td>&#160;</td>").append(td);
						$(tbl).append(tr1);
					}
				}
			};
			var frm = $("<form name='SearchForm' style=display:inline;' class='"+this.p.formclass+"'></form>");
			tbl =$("<table class='"+this.p.tableclass+"' cellspacing='0' cellpading='0' border='0'><tbody></tbody></table>");
			$(frm).append(tbl);
			formFill();
			$(this).append(frm);
			this.triggerSearch = triggerSearch;
			this.clearSearch = clearSearch;
		});
	}

});
})(jQuery);
