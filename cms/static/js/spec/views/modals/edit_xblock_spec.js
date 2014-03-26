define(["jquery", "underscore", "js/spec/create_sinon", "js/views/modals/edit_xblock", "js/models/xblock_info",
        "xmodule", "coffee/src/main", "xblock/cms.runtime.v1"],
    function ($, _, create_sinon, EditXBlockModal, XBlockInfo) {

        describe("EditXBlockModal", function() {
            var model, modal, respondWithMockXBlockEditorFragment;

            beforeEach(function () {
                model = new XBlockInfo({
                    id: 'testCourse/branch/published/block/verticalFFF',
                    display_name: 'Test Unit',
                    category: 'vertical'
                });
                modal = new EditXBlockModal({});
            });

            respondWithMockXBlockEditorFragment = function(requests, response) {
                var requestIndex = requests.length - 1;
                create_sinon.respondWithJson(requests, response, requestIndex);
            };

            describe("Editing an xblock", function() {
                var mockXBlockEditorHtml, editXBlockModalTemplate;

                beforeEach(function () {
                    window.MockXBlock = function(runtime, element) {
                        return { };
                    };
                });

                afterEach(function() {
                    window.MockXBlock = null;
                });

                mockXBlockEditorHtml = readFixtures('mock/mock-xblock-editor.underscore');
                editXBlockModalTemplate = readFixtures('edit-xblock-modal.underscore');

                it('can render itself', function() {
                    var requests, xblockElement, cancelButton;
                    requests = create_sinon.requests(this);
                    setFixtures('<div class="xblock" data-locator="mock-xblock" data-display-name="Mock XBlock"></div>');
                    appendSetFixtures($("<script>", { id: "edit-xblock-modal-tpl", type: "text/template" }).text(editXBlockModalTemplate));
                    xblockElement = $('.xblock');
                    modal.edit(xblockElement, model);

                    respondWithMockXBlockEditorFragment(requests, {
                        html: mockXBlockEditorHtml,
                        "resources": []
                    });
                    expect(modal.$('.wrapper-modal-window')).toHaveClass('is-shown');
                    cancelButton = xblockElement.select('.action-cancel');
                    expect(cancelButton.length).toBe(1);
                    cancelButton.click();
                    expect(modal.$('.wrapper-modal-window')).not.toHaveClass('is-shown');
                });
            });

            describe("Editing an xmodule", function() {
                var mockXModuleEditorHtml, editorTemplate, stringEntryTemplate, numberEntryTemplate, feedbackTemplate;

                mockXModuleEditorHtml = readFixtures('mock/mock-xmodule-editor.underscore');
                editorTemplate = readFixtures('metadata-editor.underscore');
                numberEntryTemplate = readFixtures('metadata-number-entry.underscore');
                stringEntryTemplate = readFixtures('metadata-string-entry.underscore');
                feedbackTemplate = readFixtures('system-feedback.underscore');

                beforeEach(function() {
                    setFixtures($("<script>", {id: "metadata-editor-tpl", type: "text/template"}).text(editorTemplate));
                    appendSetFixtures($("<script>", {id: "metadata-number-entry", type: "text/template"}).text(numberEntryTemplate));
                    appendSetFixtures($("<script>", {id: "metadata-string-entry", type: "text/template"}).text(stringEntryTemplate));
                    appendSetFixtures($("<script>", { id: "system-feedback-tpl", type: "text/template" }).text(feedbackTemplate));

                    // Mock the VerticalDescriptor so that the module can be rendered
                    window.VerticalDescriptor = XModule.Descriptor;
                });

                afterEach(function () {
                    window.VerticalDescriptor = null;
                });

                it('can render itself', function() {
                    var requests = create_sinon.requests(this);
                    editor.render();
                    respondWithMockXBlockEditorFragment(requests, {
                        html: mockXModuleEditorHtml,
                        "resources": []
                    });

                    expect(editor.$el.select('.xblock-header')).toBeTruthy();
                    expect(editor.getMode()).toEqual('settings');
                });
            });
        });
    });
