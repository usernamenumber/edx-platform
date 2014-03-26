define(["jquery", "underscore", "gettext", "js/views/modals/base_modal",
    "js/models/xblock_info", "js/views/xblock", "js/views/xblock_editor"],
    function($, _, gettext, BaseModal, XBlockInfo, XBlockView, XBlockEditorView) {
        var EditXBlockModal = BaseModal.extend({
            events : {
                "click .action-save": "save",
                "click .action-cancel": "cancel",
                "click .action-modes a": "changeMode"
            },

            mode: 'editor-mode',

            initialize: function() {
                this.view = this.options.view;
                this.template = _.template($("#edit-xblock-modal-tpl").text());
            },

            render: function(options) {
                var self = this,
                    editorView,
                    xblockInfo = this.xblockInfo,
                    success = options ? options.success : null;
                this.$el.html(this.template());
                editorView = new XBlockEditorView({
                    el: this.$('.xblock-editor'),
                    model: xblockInfo
                });
                this.editorView = editorView;
                editorView.render(options);
            },

            changeMode: function(event) {
                var parent = $(event.target.parentElement),
                    mode = parent.data('mode');
                event.preventDefault();
                this.selectMode(mode);
            },

            selectMode: function(mode) {
                var showEditor = mode === 'editor',
                    editorView = this.editorView,
                    editorModeButton,
                    settingsModeButton;
                editorView.selectMode(mode);
                editorModeButton = this.$('.editor-button');
                settingsModeButton = this.$('.settings-button');
                if (showEditor) {
                    editorModeButton.addClass('is-set');
                    settingsModeButton.removeClass('is-set');
                } else {
                    editorModeButton.removeClass('is-set');
                    settingsModeButton.addClass('is-set');
                }
            },

            cancel: function(event) {
                event.preventDefault();
                this.hide();
            },

            /**
             * Show an edit modal for the specified xblock
             * @param target
             * @param rootXBlockInfo
             * @param options
             */
            edit: function(xblockElement, rootXBlockInfo, options) {
                this.xblockElement = xblockElement;
                this.xblockInfo = this.findXBlockInfo(xblockElement, rootXBlockInfo);
                this.editOptions = options;
                this.render({
                    success: _.bind(this.show, this)
                });
            },

            save: function(event) {
                var self = this;
                event.preventDefault();
                this.editorView.save({
                    success: function() {
                        self.hide();
                        self.refreshXBlock();
                    }
                });
            },

            refreshXBlock: function() {
                var self = this,
                    success = self.editOptions.success,
                    xblockElement = this.xblockElement,
                    temporaryView;
                // Create a temporary view to render the updated XBlock into
                temporaryView = new XBlockView({
                    el: this.xblockElement,
                    model: this.xblockInfo,
                    view: this.view
                });
                temporaryView.render({
                    success: function() {
                        temporaryView.unbind();  // Remove the temporary view
                        if (success) {
                            success(xblockElement);
                        }
                    }
                });
            },

            findXBlockInfo: function(xblockElement, defaultXBlockInfo) {
                var xblockInfo = defaultXBlockInfo;
                if (xblockElement.length > 0) {
                    xblockInfo = new XBlockInfo({
                        'id': xblockElement.data('locator'),
                        'display-name': xblockElement.data('display-name'),
                        'category': xblockElement.data('category')
                    });
                }
                return xblockInfo;
            },

            show: function() {
                $('body').addClass('dialog-is-shown');
                this.$('.wrapper-dialog-edit-xblock').addClass('is-shown');
            },

            hide: function() {
                $('body').removeClass('modal-window-is-shown');
                this.$('.wrapper-modal-edit-xblock').removeClass('is-shown');
            }
        });

        return EditXBlockModal;
    });
