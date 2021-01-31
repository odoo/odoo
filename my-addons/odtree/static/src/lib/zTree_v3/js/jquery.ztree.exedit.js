/*
 * JQuery zTree exedit v3.5.36
 * http://treejs.cn/
 *
 * Copyright (c) 2010 Hunter.z
 *
 * Licensed same as jquery - MIT License
 * http://www.opensource.org/licenses/mit-license.php
 *
 * email: hunter.z@263.net
 * Date: 2018-06-26
 */
(function($){
	//default consts of exedit
	var _consts = {
		event: {
			DRAG: "ztree_drag",
			DROP: "ztree_drop",
			RENAME: "ztree_rename",
			DRAGMOVE:"ztree_dragmove"
		},
		id: {
			EDIT: "_edit",
			INPUT: "_input",
			REMOVE: "_remove"
		},
		move: {
			TYPE_INNER: "inner",
			TYPE_PREV: "prev",
			TYPE_NEXT: "next"
		},
		node: {
			CURSELECTED_EDIT: "curSelectedNode_Edit",
			TMPTARGET_TREE: "tmpTargetzTree",
			TMPTARGET_NODE: "tmpTargetNode"
		}
	},
	//default setting of exedit
	_setting = {
		edit: {
			enable: false,
			editNameSelectAll: false,
			showRemoveBtn: true,
			showRenameBtn: true,
			removeTitle: "remove",
			renameTitle: "rename",
			drag: {
				autoExpandTrigger: false,
				isCopy: true,
				isMove: true,
				prev: true,
				next: true,
				inner: true,
				minMoveSize: 5,
				borderMax: 10,
				borderMin: -5,
				maxShowNodeNum: 5,
				autoOpenTime: 500
			}
		},
		view: {
			addHoverDom: null,
			removeHoverDom: null
		},
		callback: {
			beforeDrag:null,
			beforeDragOpen:null,
			beforeDrop:null,
			beforeEditName:null,
			beforeRename:null,
			onDrag:null,
			onDragMove:null,
			onDrop:null,
			onRename:null
		}
	},
	//default root of exedit
	_initRoot = function (setting) {
		var r = data.getRoot(setting), rs = data.getRoots();
		r.curEditNode = null;
		r.curEditInput = null;
		r.curHoverNode = null;
		r.dragFlag = 0;
		r.dragNodeShowBefore = [];
		r.dragMaskList = new Array();
		rs.showHoverDom = true;
	},
	//default cache of exedit
	_initCache = function(treeId) {},
	//default bind event of exedit
	_bindEvent = function(setting) {
		var o = setting.treeObj;
		var c = consts.event;
		o.bind(c.RENAME, function (event, treeId, treeNode, isCancel) {
			tools.apply(setting.callback.onRename, [event, treeId, treeNode, isCancel]);
		});

		o.bind(c.DRAG, function (event, srcEvent, treeId, treeNodes) {
			tools.apply(setting.callback.onDrag, [srcEvent, treeId, treeNodes]);
		});

		o.bind(c.DRAGMOVE,function(event, srcEvent, treeId, treeNodes){
			tools.apply(setting.callback.onDragMove,[srcEvent, treeId, treeNodes]);
		});

		o.bind(c.DROP, function (event, srcEvent, treeId, treeNodes, targetNode, moveType, isCopy) {
			tools.apply(setting.callback.onDrop, [srcEvent, treeId, treeNodes, targetNode, moveType, isCopy]);
		});
	},
	_unbindEvent = function(setting) {
		var o = setting.treeObj;
		var c = consts.event;
		o.unbind(c.RENAME);
		o.unbind(c.DRAG);
		o.unbind(c.DRAGMOVE);
		o.unbind(c.DROP);
	},
	//default event proxy of exedit
	_eventProxy = function(e) {
		var target = e.target,
		setting = data.getSetting(e.data.treeId),
		relatedTarget = e.relatedTarget,
		tId = "", node = null,
		nodeEventType = "", treeEventType = "",
		nodeEventCallback = null, treeEventCallback = null,
		tmp = null;

		if (tools.eqs(e.type, "mouseover")) {
			tmp = tools.getMDom(setting, target, [{tagName:"a", attrName:"treeNode"+consts.id.A}]);
			if (tmp) {
				tId = tools.getNodeMainDom(tmp).id;
				nodeEventType = "hoverOverNode";
			}
		} else if (tools.eqs(e.type, "mouseout")) {
			tmp = tools.getMDom(setting, relatedTarget, [{tagName:"a", attrName:"treeNode"+consts.id.A}]);
			if (!tmp) {
				tId = "remove";
				nodeEventType = "hoverOutNode";
			}
		} else if (tools.eqs(e.type, "mousedown")) {
			tmp = tools.getMDom(setting, target, [{tagName:"a", attrName:"treeNode"+consts.id.A}]);
			if (tmp) {
				tId = tools.getNodeMainDom(tmp).id;
				nodeEventType = "mousedownNode";
			}
		}
		if (tId.length>0) {
			node = data.getNodeCache(setting, tId);
			switch (nodeEventType) {
				case "mousedownNode" :
					nodeEventCallback = _handler.onMousedownNode;
					break;
				case "hoverOverNode" :
					nodeEventCallback = _handler.onHoverOverNode;
					break;
				case "hoverOutNode" :
					nodeEventCallback = _handler.onHoverOutNode;
					break;
			}
		}
		var proxyResult = {
			stop: false,
			node: node,
			nodeEventType: nodeEventType,
			nodeEventCallback: nodeEventCallback,
			treeEventType: treeEventType,
			treeEventCallback: treeEventCallback
		};
		return proxyResult
	},
	//default init node of exedit
	_initNode = function(setting, level, n, parentNode, isFirstNode, isLastNode, openFlag) {
		if (!n) return;
		n.isHover = false;
		n.editNameFlag = false;
	},
	//update zTreeObj, add method of edit
	_zTreeTools = function(setting, zTreeTools) {
		zTreeTools.cancelEditName = function(newName) {
			var root = data.getRoot(this.setting);
			if (!root.curEditNode) return;
			view.cancelCurEditNode(this.setting, newName?newName:null, true);
		}
		zTreeTools.copyNode = function(targetNode, node, moveType, isSilent) {
			if (!node) return null;
      var isParent = data.nodeIsParent(setting, targetNode);
			if (targetNode && !isParent && this.setting.data.keep.leaf && moveType === consts.move.TYPE_INNER) return null;
			var _this = this,
				newNode = tools.clone(node);
			if (!targetNode) {
				targetNode = null;
				moveType = consts.move.TYPE_INNER;
			}
			if (moveType == consts.move.TYPE_INNER) {
				function copyCallback() {
					view.addNodes(_this.setting, targetNode, -1, [newNode], isSilent);
				}

				if (tools.canAsync(this.setting, targetNode)) {
					view.asyncNode(this.setting, targetNode, isSilent, copyCallback);
				} else {
					copyCallback();
				}
			} else {
				view.addNodes(this.setting, targetNode.parentNode, -1, [newNode], isSilent);
				view.moveNode(this.setting, targetNode, newNode, moveType, false, isSilent);
			}
			return newNode;
		}
		zTreeTools.editName = function(node) {
			if (!node || !node.tId || node !== data.getNodeCache(this.setting, node.tId)) return;
			if (node.parentTId) view.expandCollapseParentNode(this.setting, node.getParentNode(), true);
			view.editNode(this.setting, node)
		}
		zTreeTools.moveNode = function(targetNode, node, moveType, isSilent) {
			if (!node) return node;
      var isParent = data.nodeIsParent(setting, targetNode);
			if (targetNode && !isParent && this.setting.data.keep.leaf && moveType === consts.move.TYPE_INNER) {
				return null;
			} else if (targetNode && ((node.parentTId == targetNode.tId && moveType == consts.move.TYPE_INNER) || $$(node, this.setting).find("#" + targetNode.tId).length > 0)) {
				return null;
			} else if (!targetNode) {
				targetNode = null;
			}
			var _this = this;
			function moveCallback() {
				view.moveNode(_this.setting, targetNode, node, moveType, false, isSilent);
			}
			if (tools.canAsync(this.setting, targetNode) && moveType === consts.move.TYPE_INNER) {
				view.asyncNode(this.setting, targetNode, isSilent, moveCallback);
			} else {
				moveCallback();
			}
			return node;
		}
		zTreeTools.setEditable = function(editable) {
			this.setting.edit.enable = editable;
			return this.refresh();
		}
	},
	//method of operate data
	_data = {
		setSonNodeLevel: function(setting, parentNode, node) {
			if (!node) return;
      var children = data.nodeChildren(setting, node);
			node.level = (parentNode)? parentNode.level + 1 : 0;
			if (!children) return;
			for (var i = 0, l = children.length; i < l; i++) {
				if (children[i]) data.setSonNodeLevel(setting, node, children[i]);
			}
		}
	},
	//method of event proxy
	_event = {

	},
	//method of event handler
	_handler = {
		onHoverOverNode: function(event, node) {
			var setting = data.getSetting(event.data.treeId),
			root = data.getRoot(setting);
			if (root.curHoverNode != node) {
				_handler.onHoverOutNode(event);
			}
			root.curHoverNode = node;
			view.addHoverDom(setting, node);
		},
		onHoverOutNode: function(event, node) {
			var setting = data.getSetting(event.data.treeId),
			root = data.getRoot(setting);
			if (root.curHoverNode && !data.isSelectedNode(setting, root.curHoverNode)) {
				view.removeTreeDom(setting, root.curHoverNode);
				root.curHoverNode = null;
			}
		},
		onMousedownNode: function(eventMouseDown, _node) {
			var i,l,
			setting = data.getSetting(eventMouseDown.data.treeId),
			root = data.getRoot(setting), roots = data.getRoots();
			//right click can't drag & drop
			if (eventMouseDown.button == 2 || !setting.edit.enable || (!setting.edit.drag.isCopy && !setting.edit.drag.isMove)) return true;

			//input of edit node name can't drag & drop
			var target = eventMouseDown.target,
			_nodes = data.getRoot(setting).curSelectedList,
			nodes = [];
			if (!data.isSelectedNode(setting, _node)) {
				nodes = [_node];
			} else {
				for (i=0, l=_nodes.length; i<l; i++) {
					if (_nodes[i].editNameFlag && tools.eqs(target.tagName, "input") && target.getAttribute("treeNode"+consts.id.INPUT) !== null) {
						return true;
					}
					nodes.push(_nodes[i]);
					if (nodes[0].parentTId !== _nodes[i].parentTId) {
						nodes = [_node];
						break;
					}
				}
			}

			view.editNodeBlur = true;
			view.cancelCurEditNode(setting);

			var doc = $(setting.treeObj.get(0).ownerDocument),
			body = $(setting.treeObj.get(0).ownerDocument.body), curNode, tmpArrow, tmpTarget,
			isOtherTree = false,
			targetSetting = setting,
			sourceSetting = setting,
			preNode, nextNode,
			preTmpTargetNodeId = null,
			preTmpMoveType = null,
			tmpTargetNodeId = null,
			moveType = consts.move.TYPE_INNER,
			mouseDownX = eventMouseDown.clientX,
			mouseDownY = eventMouseDown.clientY,
			startTime = (new Date()).getTime();

			if (tools.uCanDo(setting)) {
				doc.bind("mousemove", _docMouseMove);
			}
			function _docMouseMove(event) {
				//avoid start drag after click node
				if (root.dragFlag == 0 && Math.abs(mouseDownX - event.clientX) < setting.edit.drag.minMoveSize
					&& Math.abs(mouseDownY - event.clientY) < setting.edit.drag.minMoveSize) {
					return true;
				}
				var i, l, tmpNode, tmpDom, tmpNodes;
				body.css("cursor", "pointer");

				if (root.dragFlag == 0) {
					if (tools.apply(setting.callback.beforeDrag, [setting.treeId, nodes], true) == false) {
						_docMouseUp(event);
						return true;
					}

					for (i=0, l=nodes.length; i<l; i++) {
						if (i==0) {
							root.dragNodeShowBefore = [];
						}
						tmpNode = nodes[i];
						if (data.nodeIsParent(setting, tmpNode) && tmpNode.open) {
							view.expandCollapseNode(setting, tmpNode, !tmpNode.open);
							root.dragNodeShowBefore[tmpNode.tId] = true;
						} else {
							root.dragNodeShowBefore[tmpNode.tId] = false;
						}
					}

					root.dragFlag = 1;
					roots.showHoverDom = false;
					tools.showIfameMask(setting, true);

					//sort
					var isOrder = true, lastIndex = -1;
					if (nodes.length>1) {
						var pNodes = nodes[0].parentTId ? data.nodeChildren(setting, nodes[0].getParentNode()) : data.getNodes(setting);
						tmpNodes = [];
						for (i=0, l=pNodes.length; i<l; i++) {
							if (root.dragNodeShowBefore[pNodes[i].tId] !== undefined) {
								if (isOrder && lastIndex > -1 && (lastIndex+1) !== i) {
									isOrder = false;
								}
								tmpNodes.push(pNodes[i]);
								lastIndex = i;
							}
							if (nodes.length === tmpNodes.length) {
								nodes = tmpNodes;
								break;
							}
						}
					}
					if (isOrder) {
						preNode = nodes[0].getPreNode();
						nextNode = nodes[nodes.length-1].getNextNode();
					}

					//set node in selected
					curNode = $$("<ul class='zTreeDragUL'></ul>", setting);
					for (i=0, l=nodes.length; i<l; i++) {
						tmpNode = nodes[i];
						tmpNode.editNameFlag = false;
						view.selectNode(setting, tmpNode, i>0);
						view.removeTreeDom(setting, tmpNode);

						if (i > setting.edit.drag.maxShowNodeNum-1) {
							continue;
						}

						tmpDom = $$("<li id='"+ tmpNode.tId +"_tmp'></li>", setting);
						tmpDom.append($$(tmpNode, consts.id.A, setting).clone());
						tmpDom.css("padding", "0");
						tmpDom.children("#" + tmpNode.tId + consts.id.A).removeClass(consts.node.CURSELECTED);
						curNode.append(tmpDom);
						if (i == setting.edit.drag.maxShowNodeNum-1) {
							tmpDom = $$("<li id='"+ tmpNode.tId +"_moretmp'><a>  ...  </a></li>", setting);
							curNode.append(tmpDom);
						}
					}
					curNode.attr("id", nodes[0].tId + consts.id.UL + "_tmp");
					curNode.addClass(setting.treeObj.attr("class"));
					curNode.appendTo(body);

					tmpArrow = $$("<span class='tmpzTreeMove_arrow'></span>", setting);
					tmpArrow.attr("id", "zTreeMove_arrow_tmp");
					tmpArrow.appendTo(body);

					setting.treeObj.trigger(consts.event.DRAG, [event, setting.treeId, nodes]);
				}

				if (root.dragFlag == 1) {
					if (tmpTarget && tmpArrow.attr("id") == event.target.id && tmpTargetNodeId && (event.clientX + doc.scrollLeft()+2) > ($("#" + tmpTargetNodeId + consts.id.A, tmpTarget).offset().left)) {
						var xT = $("#" + tmpTargetNodeId + consts.id.A, tmpTarget);
						event.target = (xT.length > 0) ? xT.get(0) : event.target;
					} else if (tmpTarget) {
						tmpTarget.removeClass(consts.node.TMPTARGET_TREE);
						if (tmpTargetNodeId) $("#" + tmpTargetNodeId + consts.id.A, tmpTarget).removeClass(consts.node.TMPTARGET_NODE + "_" + consts.move.TYPE_PREV)
							.removeClass(consts.node.TMPTARGET_NODE + "_" + _consts.move.TYPE_NEXT).removeClass(consts.node.TMPTARGET_NODE + "_" + _consts.move.TYPE_INNER);
					}
					tmpTarget = null;
					tmpTargetNodeId = null;

					//judge drag & drop in multi ztree
					isOtherTree = false;
					targetSetting = setting;
					var settings = data.getSettings();
					for (var s in settings) {
						if (settings[s].treeId && settings[s].edit.enable && settings[s].treeId != setting.treeId
							&& (event.target.id == settings[s].treeId || $(event.target).parents("#" + settings[s].treeId).length>0)) {
							isOtherTree = true;
							targetSetting = settings[s];
						}
					}

					var docScrollTop = doc.scrollTop(),
					docScrollLeft = doc.scrollLeft(),
					treeOffset = targetSetting.treeObj.offset(),
					scrollHeight = targetSetting.treeObj.get(0).scrollHeight,
					scrollWidth = targetSetting.treeObj.get(0).scrollWidth,
					dTop = (event.clientY + docScrollTop - treeOffset.top),
					dBottom = (targetSetting.treeObj.height() + treeOffset.top - event.clientY - docScrollTop),
					dLeft = (event.clientX + docScrollLeft - treeOffset.left),
					dRight = (targetSetting.treeObj.width() + treeOffset.left - event.clientX - docScrollLeft),
					isTop = (dTop < setting.edit.drag.borderMax && dTop > setting.edit.drag.borderMin),
					isBottom = (dBottom < setting.edit.drag.borderMax && dBottom > setting.edit.drag.borderMin),
					isLeft = (dLeft < setting.edit.drag.borderMax && dLeft > setting.edit.drag.borderMin),
					isRight = (dRight < setting.edit.drag.borderMax && dRight > setting.edit.drag.borderMin),
					isTreeInner = dTop > setting.edit.drag.borderMin && dBottom > setting.edit.drag.borderMin && dLeft > setting.edit.drag.borderMin && dRight > setting.edit.drag.borderMin,
					isTreeTop = (isTop && targetSetting.treeObj.scrollTop() <= 0),
					isTreeBottom = (isBottom && (targetSetting.treeObj.scrollTop() + targetSetting.treeObj.height()+10) >= scrollHeight),
					isTreeLeft = (isLeft && targetSetting.treeObj.scrollLeft() <= 0),
					isTreeRight = (isRight && (targetSetting.treeObj.scrollLeft() + targetSetting.treeObj.width()+10) >= scrollWidth);

					if (event.target && tools.isChildOrSelf(event.target, targetSetting.treeId)) {
						//get node <li> dom
						var targetObj = event.target;
						while (targetObj && targetObj.tagName && !tools.eqs(targetObj.tagName, "li") && targetObj.id != targetSetting.treeId) {
							targetObj = targetObj.parentNode;
						}

						var canMove = true;
						//don't move to self or children of self
						for (i=0, l=nodes.length; i<l; i++) {
							tmpNode = nodes[i];
							if (targetObj.id === tmpNode.tId) {
								canMove = false;
								break;
							} else if ($$(tmpNode, setting).find("#" + targetObj.id).length > 0) {
								canMove = false;
								break;
							}
						}
						if (canMove && event.target && tools.isChildOrSelf(event.target, targetObj.id + consts.id.A)) {
							tmpTarget = $(targetObj);
							tmpTargetNodeId = targetObj.id;
						}
					}

					//the mouse must be in zTree
					tmpNode = nodes[0];
					if (isTreeInner && tools.isChildOrSelf(event.target, targetSetting.treeId)) {
						//judge mouse move in root of ztree
						if (!tmpTarget && (event.target.id == targetSetting.treeId || isTreeTop || isTreeBottom || isTreeLeft || isTreeRight) && (isOtherTree || (!isOtherTree && tmpNode.parentTId))) {
							tmpTarget = targetSetting.treeObj;
						}
						//auto scroll top
						if (isTop) {
							targetSetting.treeObj.scrollTop(targetSetting.treeObj.scrollTop()-10);
						} else if (isBottom)  {
							targetSetting.treeObj.scrollTop(targetSetting.treeObj.scrollTop()+10);
						}
						if (isLeft) {
							targetSetting.treeObj.scrollLeft(targetSetting.treeObj.scrollLeft()-10);
						} else if (isRight) {
							targetSetting.treeObj.scrollLeft(targetSetting.treeObj.scrollLeft()+10);
						}
						//auto scroll left
						if (tmpTarget && tmpTarget != targetSetting.treeObj && tmpTarget.offset().left < targetSetting.treeObj.offset().left) {
							targetSetting.treeObj.scrollLeft(targetSetting.treeObj.scrollLeft()+ tmpTarget.offset().left - targetSetting.treeObj.offset().left);
						}
					}

					curNode.css({
						"top": (event.clientY + docScrollTop + 3) + "px",
						"left": (event.clientX + docScrollLeft + 3) + "px"
					});

					var dX = 0;
					var dY = 0;
					if (tmpTarget && tmpTarget.attr("id")!=targetSetting.treeId) {
						var tmpTargetNode = tmpTargetNodeId == null ? null: data.getNodeCache(targetSetting, tmpTargetNodeId),
							isCopy = ((event.ctrlKey || event.metaKey) && setting.edit.drag.isMove && setting.edit.drag.isCopy) || (!setting.edit.drag.isMove && setting.edit.drag.isCopy),
							isPrev = !!(preNode && tmpTargetNodeId === preNode.tId),
							isNext = !!(nextNode && tmpTargetNodeId === nextNode.tId),
							isInner = (tmpNode.parentTId && tmpNode.parentTId == tmpTargetNodeId),
							canPrev = (isCopy || !isNext) && tools.apply(targetSetting.edit.drag.prev, [targetSetting.treeId, nodes, tmpTargetNode], !!targetSetting.edit.drag.prev),
							canNext = (isCopy || !isPrev) && tools.apply(targetSetting.edit.drag.next, [targetSetting.treeId, nodes, tmpTargetNode], !!targetSetting.edit.drag.next),
							canInner = (isCopy || !isInner) && !(targetSetting.data.keep.leaf && !data.nodeIsParent(setting, tmpTargetNode)) && tools.apply(targetSetting.edit.drag.inner, [targetSetting.treeId, nodes, tmpTargetNode], !!targetSetting.edit.drag.inner);

						function clearMove() {
							tmpTarget = null;
							tmpTargetNodeId = "";
							moveType = consts.move.TYPE_INNER;
							tmpArrow.css({
								"display":"none"
							});
							if (window.zTreeMoveTimer) {
								clearTimeout(window.zTreeMoveTimer);
								window.zTreeMoveTargetNodeTId = null
							}
						}
						if (!canPrev && !canNext && !canInner) {
							clearMove();
						} else {
							var tmpTargetA = $("#" + tmpTargetNodeId + consts.id.A, tmpTarget),
								tmpNextA = tmpTargetNode.isLastNode ? null : $("#" + tmpTargetNode.getNextNode().tId + consts.id.A, tmpTarget.next()),
								tmpTop = tmpTargetA.offset().top,
								tmpLeft = tmpTargetA.offset().left,
								prevPercent = canPrev ? (canInner ? 0.25 : (canNext ? 0.5 : 1) ) : -1,
								nextPercent = canNext ? (canInner ? 0.75 : (canPrev ? 0.5 : 0) ) : -1,
								dY_percent = (event.clientY + docScrollTop - tmpTop)/tmpTargetA.height();

							if ((prevPercent==1 || dY_percent<=prevPercent && dY_percent>=-.2) && canPrev) {
								dX = 1 - tmpArrow.width();
								dY = tmpTop - tmpArrow.height()/2;
								moveType = consts.move.TYPE_PREV;
							} else if ((nextPercent==0 || dY_percent>=nextPercent && dY_percent<=1.2) && canNext) {
								dX = 1 - tmpArrow.width();
								dY = (tmpNextA == null || (data.nodeIsParent(setting, tmpTargetNode) && tmpTargetNode.open)) ? (tmpTop + tmpTargetA.height() - tmpArrow.height()/2) : (tmpNextA.offset().top - tmpArrow.height()/2);
								moveType = consts.move.TYPE_NEXT;
							} else if (canInner) {
								dX = 5 - tmpArrow.width();
								dY = tmpTop;
								moveType = consts.move.TYPE_INNER;
							} else {
								clearMove();
							}

							if (tmpTarget) {
								tmpArrow.css({
									"display":"block",
									"top": dY + "px",
									"left": (tmpLeft + dX) + "px"
								});
								tmpTargetA.addClass(consts.node.TMPTARGET_NODE + "_" + moveType);

								if (preTmpTargetNodeId != tmpTargetNodeId || preTmpMoveType != moveType) {
									startTime = (new Date()).getTime();
								}
								if (tmpTargetNode && data.nodeIsParent(setting, tmpTargetNode) && moveType == consts.move.TYPE_INNER) {
									var startTimer = true;
									if (window.zTreeMoveTimer && window.zTreeMoveTargetNodeTId !== tmpTargetNode.tId) {
										clearTimeout(window.zTreeMoveTimer);
										window.zTreeMoveTargetNodeTId = null;
									} else if (window.zTreeMoveTimer && window.zTreeMoveTargetNodeTId === tmpTargetNode.tId) {
										startTimer = false;
									}
									if (startTimer) {
										window.zTreeMoveTimer = setTimeout(function() {
											if (moveType != consts.move.TYPE_INNER) return;
											if (tmpTargetNode && data.nodeIsParent(setting, tmpTargetNode) && !tmpTargetNode.open && (new Date()).getTime() - startTime > targetSetting.edit.drag.autoOpenTime
												&& tools.apply(targetSetting.callback.beforeDragOpen, [targetSetting.treeId, tmpTargetNode], true)) {
												view.switchNode(targetSetting, tmpTargetNode);
												if (targetSetting.edit.drag.autoExpandTrigger) {
													targetSetting.treeObj.trigger(consts.event.EXPAND, [targetSetting.treeId, tmpTargetNode]);
												}
											}
										}, targetSetting.edit.drag.autoOpenTime+50);
										window.zTreeMoveTargetNodeTId = tmpTargetNode.tId;
									}
								}
							}
						}
					} else {
						moveType = consts.move.TYPE_INNER;
						if (tmpTarget && tools.apply(targetSetting.edit.drag.inner, [targetSetting.treeId, nodes, null], !!targetSetting.edit.drag.inner)) {
							tmpTarget.addClass(consts.node.TMPTARGET_TREE);
						} else {
							tmpTarget = null;
						}
						tmpArrow.css({
							"display":"none"
						});
						if (window.zTreeMoveTimer) {
							clearTimeout(window.zTreeMoveTimer);
							window.zTreeMoveTargetNodeTId = null;
						}
					}
					preTmpTargetNodeId = tmpTargetNodeId;
					preTmpMoveType = moveType;

					setting.treeObj.trigger(consts.event.DRAGMOVE, [event, setting.treeId, nodes]);
				}
				return false;
			}

			doc.bind("mouseup", _docMouseUp);
			function _docMouseUp(event) {
				if (window.zTreeMoveTimer) {
					clearTimeout(window.zTreeMoveTimer);
					window.zTreeMoveTargetNodeTId = null;
				}
				preTmpTargetNodeId = null;
				preTmpMoveType = null;
				doc.unbind("mousemove", _docMouseMove);
				doc.unbind("mouseup", _docMouseUp);
				doc.unbind("selectstart", _docSelect);
				body.css("cursor", "");
				if (tmpTarget) {
					tmpTarget.removeClass(consts.node.TMPTARGET_TREE);
					if (tmpTargetNodeId) $("#" + tmpTargetNodeId + consts.id.A, tmpTarget).removeClass(consts.node.TMPTARGET_NODE + "_" + consts.move.TYPE_PREV)
							.removeClass(consts.node.TMPTARGET_NODE + "_" + _consts.move.TYPE_NEXT).removeClass(consts.node.TMPTARGET_NODE + "_" + _consts.move.TYPE_INNER);
				}
				tools.showIfameMask(setting, false);

				roots.showHoverDom = true;
				if (root.dragFlag == 0) return;
				root.dragFlag = 0;

				var i, l, tmpNode;
				for (i=0, l=nodes.length; i<l; i++) {
					tmpNode = nodes[i];
					if (data.nodeIsParent(setting, tmpNode) && root.dragNodeShowBefore[tmpNode.tId] && !tmpNode.open) {
						view.expandCollapseNode(setting, tmpNode, !tmpNode.open);
						delete root.dragNodeShowBefore[tmpNode.tId];
					}
				}

				if (curNode) curNode.remove();
				if (tmpArrow) tmpArrow.remove();

				var isCopy = ((event.ctrlKey || event.metaKey) && setting.edit.drag.isMove && setting.edit.drag.isCopy) || (!setting.edit.drag.isMove && setting.edit.drag.isCopy);
				if (!isCopy && tmpTarget && tmpTargetNodeId && nodes[0].parentTId && tmpTargetNodeId==nodes[0].parentTId && moveType == consts.move.TYPE_INNER) {
					tmpTarget = null;
				}
				if (tmpTarget) {
					var dragTargetNode = tmpTargetNodeId == null ? null: data.getNodeCache(targetSetting, tmpTargetNodeId);
					if (tools.apply(setting.callback.beforeDrop, [targetSetting.treeId, nodes, dragTargetNode, moveType, isCopy], true) == false) {
						view.selectNodes(sourceSetting, nodes);
						return;
					}
					var newNodes = isCopy ? tools.clone(nodes) : nodes;

					function dropCallback() {
						if (isOtherTree) {
							if (!isCopy) {
								for(var i=0, l=nodes.length; i<l; i++) {
									view.removeNode(setting, nodes[i]);
								}
							}
							if (moveType == consts.move.TYPE_INNER) {
								view.addNodes(targetSetting, dragTargetNode, -1, newNodes);
							} else {
								view.addNodes(targetSetting, dragTargetNode.getParentNode(), moveType == consts.move.TYPE_PREV ? dragTargetNode.getIndex() : dragTargetNode.getIndex()+1, newNodes);
							}
						} else {
							if (isCopy && moveType == consts.move.TYPE_INNER) {
								view.addNodes(targetSetting, dragTargetNode, -1, newNodes);
							} else if (isCopy) {
								view.addNodes(targetSetting, dragTargetNode.getParentNode(), moveType == consts.move.TYPE_PREV ? dragTargetNode.getIndex() : dragTargetNode.getIndex()+1, newNodes);
							} else {
								if (moveType != consts.move.TYPE_NEXT) {
									for (i=0, l=newNodes.length; i<l; i++) {
										view.moveNode(targetSetting, dragTargetNode, newNodes[i], moveType, false);
									}
								} else {
									for (i=-1, l=newNodes.length-1; i<l; l--) {
										view.moveNode(targetSetting, dragTargetNode, newNodes[l], moveType, false);
									}
								}
							}
						}
						view.selectNodes(targetSetting, newNodes);

						var a = $$(newNodes[0], setting).get(0);
						view.scrollIntoView(setting, a);

						setting.treeObj.trigger(consts.event.DROP, [event, targetSetting.treeId, newNodes, dragTargetNode, moveType, isCopy]);
					}

					if (moveType == consts.move.TYPE_INNER && tools.canAsync(targetSetting, dragTargetNode)) {
						view.asyncNode(targetSetting, dragTargetNode, false, dropCallback);
					} else {
						dropCallback();
					}

				} else {
					view.selectNodes(sourceSetting, nodes);
					setting.treeObj.trigger(consts.event.DROP, [event, setting.treeId, nodes, null, null, null]);
				}
			}

			doc.bind("selectstart", _docSelect);
			function _docSelect() {
				return false;
			}

			// 2018-03-30 FireFox has fixed this issue.
			//Avoid FireFox's Bug
			//If zTree Div CSS set 'overflow', so drag node outside of zTree, and event.target is error.
			// if(eventMouseDown.preventDefault) {
			// 	eventMouseDown.preventDefault();
			// }
			return true;
		}
	},
	//method of tools for zTree
	_tools = {
		getAbs: function (obj) {
			var oRect = obj.getBoundingClientRect(),
			scrollTop = document.body.scrollTop+document.documentElement.scrollTop,
			scrollLeft = document.body.scrollLeft+document.documentElement.scrollLeft;
			return [oRect.left+scrollLeft,oRect.top+scrollTop];
		},
		inputFocus: function(inputObj) {
			if (inputObj.get(0)) {
				inputObj.focus();
				tools.setCursorPosition(inputObj.get(0), inputObj.val().length);
			}
		},
		inputSelect: function(inputObj) {
			if (inputObj.get(0)) {
				inputObj.focus();
				inputObj.select();
			}
		},
		setCursorPosition: function(obj, pos){
			if(obj.setSelectionRange) {
				obj.focus();
				obj.setSelectionRange(pos,pos);
			} else if (obj.createTextRange) {
				var range = obj.createTextRange();
				range.collapse(true);
				range.moveEnd('character', pos);
				range.moveStart('character', pos);
				range.select();
			}
		},
		showIfameMask: function(setting, showSign) {
			var root = data.getRoot(setting);
			//clear full mask
			while (root.dragMaskList.length > 0) {
				root.dragMaskList[0].remove();
				root.dragMaskList.shift();
			}
			if (showSign) {
				//show mask
				var iframeList = $$("iframe", setting);
				for (var i = 0, l = iframeList.length; i < l; i++) {
					var obj = iframeList.get(i),
					r = tools.getAbs(obj),
					dragMask = $$("<div id='zTreeMask_" + i + "' class='zTreeMask' style='top:" + r[1] + "px; left:" + r[0] + "px; width:" + obj.offsetWidth + "px; height:" + obj.offsetHeight + "px;'></div>", setting);
					dragMask.appendTo($$("body", setting));
					root.dragMaskList.push(dragMask);
				}
			}
		}
	},
	//method of operate ztree dom
	_view = {
		addEditBtn: function(setting, node) {
			if (node.editNameFlag || $$(node, consts.id.EDIT, setting).length > 0) {
				return;
			}
			if (!tools.apply(setting.edit.showRenameBtn, [setting.treeId, node], setting.edit.showRenameBtn)) {
				return;
			}
			var aObj = $$(node, consts.id.A, setting),
			editStr = "<span class='" + consts.className.BUTTON + " edit' id='" + node.tId + consts.id.EDIT + "' title='"+tools.apply(setting.edit.renameTitle, [setting.treeId, node], setting.edit.renameTitle)+"' treeNode"+consts.id.EDIT+" style='display:none;'></span>";
			aObj.append(editStr);

			$$(node, consts.id.EDIT, setting).bind('click',
				function() {
					if (!tools.uCanDo(setting) || tools.apply(setting.callback.beforeEditName, [setting.treeId, node], true) == false) return false;
					view.editNode(setting, node);
					return false;
				}
				).show();
		},
		addRemoveBtn: function(setting, node) {
			if (node.editNameFlag || $$(node, consts.id.REMOVE, setting).length > 0) {
				return;
			}
			if (!tools.apply(setting.edit.showRemoveBtn, [setting.treeId, node], setting.edit.showRemoveBtn)) {
				return;
			}
			var aObj = $$(node, consts.id.A, setting),
			removeStr = "<span class='" + consts.className.BUTTON + " remove' id='" + node.tId + consts.id.REMOVE + "' title='"+tools.apply(setting.edit.removeTitle, [setting.treeId, node], setting.edit.removeTitle)+"' treeNode"+consts.id.REMOVE+" style='display:none;'></span>";
			aObj.append(removeStr);

			$$(node, consts.id.REMOVE, setting).bind('click',
				function() {
					if (!tools.uCanDo(setting) || tools.apply(setting.callback.beforeRemove, [setting.treeId, node], true) == false) return false;
					view.removeNode(setting, node);
					setting.treeObj.trigger(consts.event.REMOVE, [setting.treeId, node]);
					return false;
				}
				).bind('mousedown',
				function(eventMouseDown) {
					return true;
				}
				).show();
		},
		addHoverDom: function(setting, node) {
			if (data.getRoots().showHoverDom) {
				node.isHover = true;
				if (setting.edit.enable) {
					view.addEditBtn(setting, node);
					view.addRemoveBtn(setting, node);
				}
				tools.apply(setting.view.addHoverDom, [setting.treeId, node]);
			}
		},
		cancelCurEditNode: function (setting, forceName, isCancel) {
			var root = data.getRoot(setting),
			node = root.curEditNode;

			if (node) {
				var inputObj = root.curEditInput,
				newName = forceName ? forceName:(isCancel ? data.nodeName(setting, node): inputObj.val());
				if (tools.apply(setting.callback.beforeRename, [setting.treeId, node, newName, isCancel], true) === false) {
					return false;
				}
        data.nodeName(setting, node, newName);
				var aObj = $$(node, consts.id.A, setting);
				aObj.removeClass(consts.node.CURSELECTED_EDIT);
				inputObj.unbind();
				view.setNodeName(setting, node);
				node.editNameFlag = false;
				root.curEditNode = null;
				root.curEditInput = null;
				view.selectNode(setting, node, false);
				setting.treeObj.trigger(consts.event.RENAME, [setting.treeId, node, isCancel]);
			}
			root.noSelection = true;
			return true;
		},
		editNode: function(setting, node) {
			var root = data.getRoot(setting);
			view.editNodeBlur = false;
			if (data.isSelectedNode(setting, node) && root.curEditNode == node && node.editNameFlag) {
				setTimeout(function() {tools.inputFocus(root.curEditInput);}, 0);
				return;
			}
			node.editNameFlag = true;
			view.removeTreeDom(setting, node);
			view.cancelCurEditNode(setting);
			view.selectNode(setting, node, false);
			$$(node, consts.id.SPAN, setting).html("<input type=text class='rename' id='" + node.tId + consts.id.INPUT + "' treeNode" + consts.id.INPUT + " >");
			var inputObj = $$(node, consts.id.INPUT, setting);
			inputObj.attr("value", data.nodeName(setting, node));
			if (setting.edit.editNameSelectAll) {
				tools.inputSelect(inputObj);
			} else {
				tools.inputFocus(inputObj);
			}

			inputObj.bind('blur', function(event) {
				if (!view.editNodeBlur) {
					view.cancelCurEditNode(setting);
				}
			}).bind('keydown', function(event) {
				if (event.keyCode=="13") {
					view.editNodeBlur = true;
					view.cancelCurEditNode(setting);
				} else if (event.keyCode=="27") {
					view.cancelCurEditNode(setting, null, true);
				}
			}).bind('click', function(event) {
				return false;
			}).bind('dblclick', function(event) {
				return false;
			});

			$$(node, consts.id.A, setting).addClass(consts.node.CURSELECTED_EDIT);
			root.curEditInput = inputObj;
			root.noSelection = false;
			root.curEditNode = node;
		},
		moveNode: function(setting, targetNode, node, moveType, animateFlag, isSilent) {
			var root = data.getRoot(setting);
			if (targetNode == node) return;
			if (setting.data.keep.leaf && targetNode && !data.nodeIsParent(setting, targetNode) && moveType == consts.move.TYPE_INNER) return;
			var oldParentNode = (node.parentTId ? node.getParentNode(): root),
			targetNodeIsRoot = (targetNode === null || targetNode == root);
			if (targetNodeIsRoot && targetNode === null) targetNode = root;
			if (targetNodeIsRoot) moveType = consts.move.TYPE_INNER;
			var targetParentNode = (targetNode.parentTId ? targetNode.getParentNode() : root);

			if (moveType != consts.move.TYPE_PREV && moveType != consts.move.TYPE_NEXT) {
				moveType = consts.move.TYPE_INNER;
			}

			if (moveType == consts.move.TYPE_INNER) {
				if (targetNodeIsRoot) {
					//parentTId of root node is null
					node.parentTId = null;
				} else {
					if (!data.nodeIsParent(setting, targetNode)) {
            data.nodeIsParent(setting, targetNode, true);
						targetNode.open = !!targetNode.open;
						view.setNodeLineIcos(setting, targetNode);
					}
					node.parentTId = targetNode.tId;
				}
			}

			//move node Dom
			var targetObj, target_ulObj;
			if (targetNodeIsRoot) {
				targetObj = setting.treeObj;
				target_ulObj = targetObj;
			} else {
				if (!isSilent && moveType == consts.move.TYPE_INNER) {
					view.expandCollapseNode(setting, targetNode, true, false);
				} else if (!isSilent) {
					view.expandCollapseNode(setting, targetNode.getParentNode(), true, false);
				}
				targetObj = $$(targetNode, setting);
				target_ulObj = $$(targetNode, consts.id.UL, setting);
				if (!!targetObj.get(0) && !target_ulObj.get(0)) {
					var ulstr = [];
					view.makeUlHtml(setting, targetNode, ulstr, '');
					targetObj.append(ulstr.join(''));
				}
				target_ulObj = $$(targetNode, consts.id.UL, setting);
			}
			var nodeDom = $$(node, setting);
			if (!nodeDom.get(0)) {
				nodeDom = view.appendNodes(setting, node.level, [node], null, -1, false, true).join('');
			} else if (!targetObj.get(0)) {
				nodeDom.remove();
			}
			if (target_ulObj.get(0) && moveType == consts.move.TYPE_INNER) {
				target_ulObj.append(nodeDom);
			} else if (targetObj.get(0) && moveType == consts.move.TYPE_PREV) {
				targetObj.before(nodeDom);
			} else if (targetObj.get(0) && moveType == consts.move.TYPE_NEXT) {
				targetObj.after(nodeDom);
			}

			//repair the data after move
			var i,l,
			tmpSrcIndex = -1,
			tmpTargetIndex = 0,
			oldNeighbor = null,
			newNeighbor = null,
			oldLevel = node.level;
			var oldChildren = data.nodeChildren(setting, oldParentNode);
			var targetParentChildren = data.nodeChildren(setting, targetParentNode);
			var targetChildren = data.nodeChildren(setting, targetNode);
			if (node.isFirstNode) {
				tmpSrcIndex = 0;
				if (oldChildren.length > 1 ) {
					oldNeighbor = oldChildren[1];
					oldNeighbor.isFirstNode = true;
				}
			} else if (node.isLastNode) {
				tmpSrcIndex = oldChildren.length -1;
				oldNeighbor = oldChildren[tmpSrcIndex - 1];
				oldNeighbor.isLastNode = true;
			} else {
				for (i = 0, l = oldChildren.length; i < l; i++) {
					if (oldChildren[i].tId == node.tId) {
						tmpSrcIndex = i;
						break;
					}
				}
			}
			if (tmpSrcIndex >= 0) {
				oldChildren.splice(tmpSrcIndex, 1);
			}
			if (moveType != consts.move.TYPE_INNER) {
				for (i = 0, l = targetParentChildren.length; i < l; i++) {
					if (targetParentChildren[i].tId == targetNode.tId) tmpTargetIndex = i;
				}
			}
			if (moveType == consts.move.TYPE_INNER) {
				if (!targetChildren) {
          targetChildren = data.nodeChildren(setting, targetNode, []);
        }
				if (targetChildren.length > 0) {
					newNeighbor = targetChildren[targetChildren.length - 1];
					newNeighbor.isLastNode = false;
				}
				targetChildren.splice(targetChildren.length, 0, node);
				node.isLastNode = true;
				node.isFirstNode = (targetChildren.length == 1);
			} else if (targetNode.isFirstNode && moveType == consts.move.TYPE_PREV) {
				targetParentChildren.splice(tmpTargetIndex, 0, node);
				newNeighbor = targetNode;
				newNeighbor.isFirstNode = false;
				node.parentTId = targetNode.parentTId;
				node.isFirstNode = true;
				node.isLastNode = false;

			} else if (targetNode.isLastNode && moveType == consts.move.TYPE_NEXT) {
				targetParentChildren.splice(tmpTargetIndex + 1, 0, node);
				newNeighbor = targetNode;
				newNeighbor.isLastNode = false;
				node.parentTId = targetNode.parentTId;
				node.isFirstNode = false;
				node.isLastNode = true;

			} else {
				if (moveType == consts.move.TYPE_PREV) {
					targetParentChildren.splice(tmpTargetIndex, 0, node);
				} else {
					targetParentChildren.splice(tmpTargetIndex + 1, 0, node);
				}
				node.parentTId = targetNode.parentTId;
				node.isFirstNode = false;
				node.isLastNode = false;
			}
			data.fixPIdKeyValue(setting, node);
			data.setSonNodeLevel(setting, node.getParentNode(), node);

			//repair node what been moved
			view.setNodeLineIcos(setting, node);
			view.repairNodeLevelClass(setting, node, oldLevel);

			//repair node's old parentNode dom
			if (!setting.data.keep.parent && oldChildren.length < 1) {
				//old parentNode has no child nodes
        data.nodeIsParent(setting, oldParentNode, false);
				oldParentNode.open = false;
				var tmp_ulObj = $$(oldParentNode, consts.id.UL, setting),
				tmp_switchObj = $$(oldParentNode, consts.id.SWITCH, setting),
				tmp_icoObj = $$(oldParentNode, consts.id.ICON, setting);
				view.replaceSwitchClass(oldParentNode, tmp_switchObj, consts.folder.DOCU);
				view.replaceIcoClass(oldParentNode, tmp_icoObj, consts.folder.DOCU);
				tmp_ulObj.css("display", "none");

			} else if (oldNeighbor) {
				//old neigbor node
				view.setNodeLineIcos(setting, oldNeighbor);
			}

			//new neigbor node
			if (newNeighbor) {
				view.setNodeLineIcos(setting, newNeighbor);
			}

			//repair checkbox / radio
			if (!!setting.check && setting.check.enable && view.repairChkClass) {
				view.repairChkClass(setting, oldParentNode);
				view.repairParentChkClassWithSelf(setting, oldParentNode);
				if (oldParentNode != node.parent)
					view.repairParentChkClassWithSelf(setting, node);
			}

			//expand parents after move
			if (!isSilent) {
				view.expandCollapseParentNode(setting, node.getParentNode(), true, animateFlag);
			}
		},
		removeEditBtn: function(setting, node) {
			$$(node, consts.id.EDIT, setting).unbind().remove();
		},
		removeRemoveBtn: function(setting, node) {
			$$(node, consts.id.REMOVE, setting).unbind().remove();
		},
		removeTreeDom: function(setting, node) {
			node.isHover = false;
			view.removeEditBtn(setting, node);
			view.removeRemoveBtn(setting, node);
			tools.apply(setting.view.removeHoverDom, [setting.treeId, node]);
		},
		repairNodeLevelClass: function(setting, node, oldLevel) {
			if (oldLevel === node.level) return;
			var liObj = $$(node, setting),
			aObj = $$(node, consts.id.A, setting),
			ulObj = $$(node, consts.id.UL, setting),
			oldClass = consts.className.LEVEL + oldLevel,
			newClass = consts.className.LEVEL + node.level;
			liObj.removeClass(oldClass);
			liObj.addClass(newClass);
			aObj.removeClass(oldClass);
			aObj.addClass(newClass);
			ulObj.removeClass(oldClass);
			ulObj.addClass(newClass);
		},
		selectNodes : function(setting, nodes) {
			for (var i=0, l=nodes.length; i<l; i++) {
				view.selectNode(setting, nodes[i], i>0);
			}
		}
	},

	_z = {
		tools: _tools,
		view: _view,
		event: _event,
		data: _data
	};
	$.extend(true, $.fn.zTree.consts, _consts);
	$.extend(true, $.fn.zTree._z, _z);

	var zt = $.fn.zTree,
	tools = zt._z.tools,
	consts = zt.consts,
	view = zt._z.view,
	data = zt._z.data,
	event = zt._z.event,
	$$ = tools.$;

	data.exSetting(_setting);
	data.addInitBind(_bindEvent);
	data.addInitUnBind(_unbindEvent);
	data.addInitCache(_initCache);
	data.addInitNode(_initNode);
	data.addInitProxy(_eventProxy);
	data.addInitRoot(_initRoot);
	data.addZTreeTools(_zTreeTools);

	var _cancelPreSelectedNode = view.cancelPreSelectedNode;
	view.cancelPreSelectedNode = function (setting, node) {
		var list = data.getRoot(setting).curSelectedList;
		for (var i=0, j=list.length; i<j; i++) {
			if (!node || node === list[i]) {
				view.removeTreeDom(setting, list[i]);
				if (node) break;
			}
		}
		if (_cancelPreSelectedNode) _cancelPreSelectedNode.apply(view, arguments);
	}

	var _createNodes = view.createNodes;
	view.createNodes = function(setting, level, nodes, parentNode, index) {
		if (_createNodes) {
			_createNodes.apply(view, arguments);
		}
		if (!nodes) return;
		if (view.repairParentChkClassWithSelf) {
			view.repairParentChkClassWithSelf(setting, parentNode);
		}
	}

	var _makeNodeUrl = view.makeNodeUrl;
	view.makeNodeUrl = function(setting, node) {
		return setting.edit.enable ? null : (_makeNodeUrl.apply(view, arguments));
	}

	var _removeNode = view.removeNode;
	view.removeNode = function(setting, node) {
		var root = data.getRoot(setting);
		if (root.curEditNode === node) root.curEditNode = null;
		if (_removeNode) {
			_removeNode.apply(view, arguments);
		}
	}

	var _selectNode = view.selectNode;
	view.selectNode = function(setting, node, addFlag) {
		var root = data.getRoot(setting);
		if (data.isSelectedNode(setting, node) && root.curEditNode == node && node.editNameFlag) {
			return false;
		}
		if (_selectNode) _selectNode.apply(view, arguments);
		view.addHoverDom(setting, node);
		return true;
	}

	var _uCanDo = tools.uCanDo;
	tools.uCanDo = function(setting, e) {
		var root = data.getRoot(setting);
		if (e && (tools.eqs(e.type, "mouseover") || tools.eqs(e.type, "mouseout") || tools.eqs(e.type, "mousedown") || tools.eqs(e.type, "mouseup"))) {
			return true;
		}
		if (root.curEditNode) {
			view.editNodeBlur = false;
			root.curEditInput.focus();
		}
		return (!root.curEditNode) && (_uCanDo ? _uCanDo.apply(view, arguments) : true);
	}
})(jQuery);