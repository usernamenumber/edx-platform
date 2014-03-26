define([ "jquery", "js/spec/create_sinon", "URI", "js/views/xblock_container", "js/models/xblock_info",
    "xmodule", "coffee/src/main", "xblock/cms.runtime.v1"],
    function ($, create_sinon, URI, XBlockContainerView, XBlockInfo) {

        describe("XBlockContainerView", function() {
            var model, editor, respondWithMockXBlockEditorFragment;

            beforeEach(function () {
                model = new XBlockInfo({
                    id: 'testCourse/branch/published/block/verticalFFF',
                    display_name: 'Test Unit',
                    category: 'vertical'
                });
                editor = new XBlockContainerView({
                    model: model
                });
            });

            respondWithMockXBlockEditorFragment = function(requests, response) {
                var requestIndex = requests.length - 1;
                create_sinon.respondWithJson(requests, response, requestIndex);
            };

            describe("Editing an xblock", function() {
                var mockXBlockEditorHtml;

                beforeEach(function () {
                    window.MockXBlock = function(runtime, element) {
                        return { };
                    };
                });

                afterEach(function() {
                    window.MockXBlock = null;
                });

                mockXBlockEditorHtml = readFixtures('mock/mock-xblock-editor.underscore');

                it('can render itself', function() {
                    var requests = create_sinon.requests(this);
                    editor.render();
                    respondWithMockXBlockEditorFragment(requests, {
                        html: mockXBlockEditorHtml,
                        "resources": []
                    });

                    expect(editor.$el.select('.xblock-header')).toBeTruthy();
                    expect(editor.getMode()).toEqual('editor');
                });
            });
        });
    });
