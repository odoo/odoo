;(function($){
/**
 * jqGrid extension for manipulating Grid Data
 * Tony Tomov tony@trirand.com
 * http://trirand.com/blog/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl-2.0.html
**/ 
$.jgrid.extend({
//Editing
	editRow : function(rowid,keys,oneditfunc,succesfunc, url, extraparam, aftersavefunc,errorfunc, afterrestorefunc) {
		return this.each(function(){
			var $t = this, nm, tmp, editable, cnt=0, focus=null, svr={}, ind,cm;
			if (!$t.grid ) { return; }
			ind = $($t).jqGrid("getInd",rowid,true);
			if( ind === false ) {return;}
			editable = $(ind).attr("editable") || "0";
			if (editable == "0" && !$(ind).hasClass("not-editable-row")) {
				cm = $t.p.colModel;
				$('td',ind).each( function(i) {
					nm = cm[i].name;
					var treeg = $t.p.treeGrid===true && nm == $t.p.ExpandColumn;
					if(treeg) { tmp = $("span:first",this).html();}
					else {
						try {
							tmp =  $.unformat(this,{rowId:rowid, colModel:cm[i]},i);
						} catch (_) {
							tmp = $(this).html();
						}
					}
					if ( nm != 'cb' && nm != 'subgrid' && nm != 'rn') {
						if($t.p.autoencode) { tmp = $.jgrid.htmlDecode(tmp); }
						svr[nm]=tmp;
						if(cm[i].editable===true) {
							if(focus===null) { focus = i; }
							if (treeg) { $("span:first",this).html(""); }
							else { $(this).html(""); }
							var opt = $.extend({},cm[i].editoptions || {},{id:rowid+"_"+nm,name:nm});
							if(!cm[i].edittype) { cm[i].edittype = "text"; }
							var elc = $.jgrid.createEl(cm[i].edittype,opt,tmp,true,$.extend({},$.jgrid.ajaxOptions,$t.p.ajaxSelectOptions || {}));
							$(elc).addClass("editable");
							if(treeg) { $("span:first",this).append(elc); }
							else { $(this).append(elc); }
							//Again IE
							if(cm[i].edittype == "select" && cm[i].editoptions.multiple===true && $.browser.msie) {
								$(elc).width($(elc).width());
							}
							cnt++;
						}
					}
				});
				if(cnt > 0) {
					svr.id = rowid; $t.p.savedRow.push(svr);
					$(ind).attr("editable","1");
					$("td:eq("+focus+") input",ind).focus();
					if(keys===true) {
						$(ind).bind("keydown",function(e) {
							if (e.keyCode === 27) {$($t).jqGrid("restoreRow",rowid, afterrestorefunc);}
							if (e.keyCode === 13) {
								var ta = e.target;
								if(ta.tagName == 'TEXTAREA') { return true; }
								$($t).jqGrid("saveRow",rowid,succesfunc, url, extraparam, aftersavefunc,errorfunc, afterrestorefunc );
								return false;
							}
							e.stopPropagation();
						});
					}
					if( $.isFunction(oneditfunc)) { oneditfunc.call($t, rowid); }
				}
			}
		});
	},
	saveRow : function(rowid, succesfunc, url, extraparam, aftersavefunc,errorfunc, afterrestorefunc) {
		return this.each(function(){
		var $t = this, nm, tmp={}, tmp2={}, editable, fr, cv, ind;
		if (!$t.grid ) { return; }
		ind = $($t).jqGrid("getInd",rowid,true);
		if(ind === false) {return;}
		editable = $(ind).attr("editable");
		url = url ? url : $t.p.editurl;
		if (editable==="1") {
			var cm;
			$("td",ind).each(function(i) {
				cm = $t.p.colModel[i];
				nm = cm.name;
				if ( nm != 'cb' && nm != 'subgrid' && cm.editable===true && nm != 'rn') {
					switch (cm.edittype) {
						case "checkbox":
							var cbv = ["Yes","No"];
							if(cm.editoptions ) {
								cbv = cm.editoptions.value.split(":");
							}
							tmp[nm]=  $("input",this).attr("checked") ? cbv[0] : cbv[1]; 
							break;
						case 'text':
						case 'password':
						case 'textarea':
						case "button" :
							tmp[nm]=$("input, textarea",this).val();
							break;
						case 'select':
							if(!cm.editoptions.multiple) {
								tmp[nm] = $("select>option:selected",this).val();
								tmp2[nm] = $("select>option:selected", this).text();
							} else {
								var sel = $("select",this), selectedText = [];
								tmp[nm] = $(sel).val();
								if(tmp[nm]) { tmp[nm]= tmp[nm].join(","); } else { tmp[nm] =""; }
								$("select > option:selected",this).each(
									function(i,selected){
										selectedText[i] = $(selected).text();
									}
								);
								tmp2[nm] = selectedText.join(",");
							}
							if(cm.formatter && cm.formatter == 'select') { tmp2={}; }
							break;
						case 'custom' :
							try {
								if(cm.editoptions && $.isFunction(cm.editoptions.custom_value)) {
									tmp[nm] = cm.editoptions.custom_value.call($t, $(".customelement",this),'get');
									if (tmp[nm] === undefined) { throw "e2"; }
								} else { throw "e1"; }
							} catch (e) {
								if (e=="e1") { $.jgrid.info_dialog(jQuery.jgrid.errors.errcap,"function 'custom_value' "+$.jgrid.edit.msg.nodefined,jQuery.jgrid.edit.bClose); }
								if (e=="e2") { $.jgrid.info_dialog(jQuery.jgrid.errors.errcap,"function 'custom_value' "+$.jgrid.edit.msg.novalue,jQuery.jgrid.edit.bClose); }
								else { $.jgrid.info_dialog(jQuery.jgrid.errors.errcap,e.message,jQuery.jgrid.edit.bClose); }
							}
							break;
					}
					cv = $.jgrid.checkValues(tmp[nm],i,$t);
					if(cv[0] === false) {
						cv[1] = tmp[nm] + " " + cv[1];
						return false;
					}
					if($t.p.autoencode) { tmp[nm] = $.jgrid.htmlEncode(tmp[nm]); }
				}
			});
			if (cv[0] === false){
				try {
					var positions = $.jgrid.findPos($("#"+$.jgrid.jqID(rowid), $t.grid.bDiv)[0]);
					$.jgrid.info_dialog($.jgrid.errors.errcap,cv[1],$.jgrid.edit.bClose,{left:positions[0],top:positions[1]});
				} catch (e) {
					alert(cv[1]);
				}
				return;
			}
			if(tmp) {
				var idname, opers, oper;
				opers = $t.p.prmNames;
				oper = opers.oper;
				idname = opers.id;
				tmp[oper] = opers.editoper;
				tmp[idname] = rowid;
				if(typeof($t.p.inlineData) == 'undefined') { $t.p.inlineData ={}; }
				if(typeof(extraparam) == 'undefined') { extraparam ={}; }
				tmp = $.extend({},tmp,$t.p.inlineData,extraparam);
			}
			if (url == 'clientArray') {
				tmp = $.extend({},tmp, tmp2);
				if($t.p.autoencode) {
					$.each(tmp,function(n,v){
						tmp[n] = $.jgrid.htmlDecode(v);
					});
				}
				var resp = $($t).jqGrid("setRowData",rowid,tmp);
				$(ind).attr("editable","0");
				for( var k=0;k<$t.p.savedRow.length;k++) {
					if( $t.p.savedRow[k].id == rowid) {fr = k; break;}
				}
				if(fr >= 0) { $t.p.savedRow.splice(fr,1); }
				if( $.isFunction(aftersavefunc) ) { aftersavefunc.call($t, rowid,resp); }
			} else {
				$("#lui_"+$t.p.id).show();
				$.ajax($.extend({
					url:url,
					data: $.isFunction($t.p.serializeRowData) ? $t.p.serializeRowData.call($t, tmp) : tmp,
					type: "POST",
					complete: function(res,stat){
						$("#lui_"+$t.p.id).hide();
						if (stat === "success"){
							var ret;
							if( $.isFunction(succesfunc)) { ret = succesfunc.call($t, res);}
							else { ret = true; }
							if (ret===true) {
								if($t.p.autoencode) {
									$.each(tmp,function(n,v){
										tmp[n] = $.jgrid.htmlDecode(v);
									});
								}
								tmp = $.extend({},tmp, tmp2);
								$($t).jqGrid("setRowData",rowid,tmp);
								$(ind).attr("editable","0");
								for( var k=0;k<$t.p.savedRow.length;k++) {
									if( $t.p.savedRow[k].id == rowid) {fr = k; break;}
								}
								if(fr >= 0) { $t.p.savedRow.splice(fr,1); }
								if( $.isFunction(aftersavefunc) ) { aftersavefunc.call($t, rowid,res); }
							} else {
								if($.isFunction(errorfunc) ) {
									errorfunc.call($t, rowid, res, stat);
								}
								$($t).jqGrid("restoreRow",rowid, afterrestorefunc);
							}
						}
					},
					error:function(res,stat){
						$("#lui_"+$t.p.id).hide();
						if($.isFunction(errorfunc) ) {
							errorfunc.call($t, rowid, res, stat);
						} else {
							alert("Error Row: "+rowid+" Result: " +res.status+":"+res.statusText+" Status: "+stat);
						}
						$($t).jqGrid("restoreRow",rowid, afterrestorefunc);
					}
				}, $.jgrid.ajaxOptions, $t.p.ajaxRowOptions || {}));
			}
			$(ind).unbind("keydown");
		}
		});
	},
	restoreRow : function(rowid, afterrestorefunc) {
		return this.each(function(){
			var $t= this, fr, ind, ares={};
			if (!$t.grid ) { return; }
			ind = $($t).jqGrid("getInd",rowid,true);
			if(ind === false) {return;}
			for( var k=0;k<$t.p.savedRow.length;k++) {
				if( $t.p.savedRow[k].id == rowid) {fr = k; break;}
			}
			if(fr >= 0) {
				if($.isFunction($.fn.datepicker)) {
					try {
						$("input.hasDatepicker","#"+$.jgrid.jqID(ind.id)).datepicker('hide');
					} catch (e) {}
				}
				$.each($t.p.colModel, function(i,n){
					if(this.editable === true && this.name in $t.p.savedRow[fr]) {
						ares[this.name] = $t.p.savedRow[fr][this.name];
					}
				});
				$($t).jqGrid("setRowData",rowid,ares);
				$(ind).attr("editable","0").unbind("keydown");
				$t.p.savedRow.splice(fr,1);
			}
			if ($.isFunction(afterrestorefunc))
			{
				afterrestorefunc.call($t, rowid);
			}
		});
	}
//end inline edit
});
})(jQuery);
