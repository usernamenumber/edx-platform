define(["jquery", "underscore", "js/spec/create_sinon", "js/views/modals/edit_xblock", "js/models/xblock_info",
    "xmodule", "coffee/src/main", "xblock/cms.runtime.v1"],
    function ($, _, create_sinon, EditXBlockModal, XBlockInfo) {

        describe("EditXBlockModal", function() {
            var model, modal, respondWithMockXBlockEditorFragment, editXBlockModalTemplate, editorModeButtonTemplate,
                feedbackTemplate, showModal, cancelModal;

            editXBlockModalTemplate = readFixtures('edit-xblock-modal.underscore');
            editorModeButtonTemplate = readFixtures('editor-mode-button.underscore');
            feedbackTemplate = readFixtures('system-feedback.underscore');

            beforeEach(function () {
                setFixtures('<div class="xblock" data-locator="mock-xblock" data-display-name="Mock XBlock"></div>');
                appendSetFixtures($("<script>", { id: "edit-xblock-modal-tpl", type: "text/template" }).text(editXBlockModalTemplate));
                appendSetFixtures($("<script>", { id: "editor-mode-button-tpl", type: "text/template" }).text(editorModeButtonTemplate));
                appendSetFixtures($("<script>", { id: "system-feedback-tpl", type: "text/template" }).text(feedbackTemplate));
                model = new XBlockInfo({
                    id: 'testCourse/branch/published/block/verticalFFF',
                    display_name: 'Test Unit',
                    category: 'vertical'
                });
            });

            respondWithMockXBlockEditorFragment = function(requests, response) {
                var requestIndex = requests.length - 1;
                create_sinon.respondWithJson(requests, response, requestIndex);
            };

            showModal = function(requests, mockHtml) {
                var modal = new EditXBlockModal({}),
                    xblockElement = $('.xblock');
                modal.edit(xblockElement, model);
                respondWithMockXBlockEditorFragment(requests, {
                    html: mockHtml,
                    "resources": []
                });
                return modal;
            };

            cancelModal = function(modal) {
                var cancelButton = modal.$('.action-cancel');
                expect(cancelButton.length).toBe(1);
                cancelButton.click();
            };

            describe("Editing an xblock", function() {
                var mockXBlockEditorHtml;

                mockXBlockEditorHtml = readFixtures('mock/mock-xblock-editor.underscore');

                beforeEach(function () {
                    window.MockXBlock = function(runtime, element) {
                        return { };
                    };
                });

                afterEach(function() {
                    window.MockXBlock = null;
                });

                it('can show itself', function() {
                    var requests = create_sinon.requests(this);
                    modal = showModal(requests, mockXBlockEditorHtml);
                    expect(modal.$('.wrapper-modal-window')).toHaveClass('is-shown');
                    cancelModal(modal);
                    expect(modal.$('.wrapper-modal-window')).not.toHaveClass('is-shown');
                });

                it('does not show any editor mode buttons', function() {
                    var requests = create_sinon.requests(this);
                    modal = showModal(requests, mockXBlockEditorHtml);
                    expect(modal.$('.editor-modes a').length).toBe(0);
                    cancelModal(modal);
                });
            });

            describe("Editing an xmodule", function() {
                var mockXModuleEditorHtml, editorTemplate, stringEntryTemplate, numberEntryTemplate;

                mockXModuleEditorHtml = readFixtures('mock/mock-xmodule-editor.underscore');
                editorTemplate = readFixtures('metadata-editor.underscore');
                numberEntryTemplate = readFixtures('metadata-number-entry.underscore');
                stringEntryTemplate = readFixtures('metadata-string-entry.underscore');

                beforeEach(function() {
                    appendSetFixtures($("<script>", {id: "metadata-editor-tpl", type: "text/template"}).text(editorTemplate));
                    appendSetFixtures($("<script>", {id: "metadata-number-entry", type: "text/template"}).text(numberEntryTemplate));
                    appendSetFixtures($("<script>", {id: "metadata-string-entry", type: "text/template"}).text(stringEntryTemplate));

                    // Mock the VerticalDescriptor so that the module can be rendered
                    window.VerticalDescriptor = XModule.Descriptor;
                });

                afterEach(function () {
                    window.VerticalDescriptor = null;
                });

                it('can render itself', function() {
                    var requests = create_sinon.requests(this);

                    // Show the modal using a mock xblock response
                    modal = showModal(requests, mockXModuleEditorHtml);
                    expect(modal.$('.wrapper-modal-window')).toHaveClass('is-shown');
                    cancelModal(modal);
                    expect(modal.$('.wrapper-modal-window')).not.toHaveClass('is-shown');
                });

                it('shows the correct default buttons', function() {
                    var requests = create_sinon.requests(this),
                        editorButton,
                        settingsButton;
                    modal = showModal(requests, mockXModuleEditorHtml);
                    expect(modal.$('.editor-modes a').length).toBe(2);
                    editorButton = modal.$('.editor-button');
                    settingsButton = modal.$('.settings-button');
                    expect(editorButton.length).toBe(1);
                    expect(editorButton).toHaveClass('is-set');
                    expect(settingsButton.length).toBe(1);
                    expect(settingsButton).not.toHaveClass('is-set');
                    cancelModal(modal);
                });
            });
        });
    });
