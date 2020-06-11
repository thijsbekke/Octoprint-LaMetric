$(function() {
    function LaMetricViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[1];

        self.testActive = ko.observable(false);
        self.testResult = ko.observable(false);
        self.testSuccessful = ko.observable(false);
        self.testMessage = ko.observable();

        self.testNotification  = function() {
            self.testActive(true);
            self.testResult(false);
            self.testSuccessful(false);
            self.testMessage("");

            var key = $('#key').val();
            var host = $('#host').val();

            var payload = {
                command: "test",
                key: key,
                host: host,
            };

            $.ajax({
                url: API_BASEURL + "plugin/lametric",
                type: "POST",
                dataType: "json",
                data: JSON.stringify(payload),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    self.testResult(true);
                    self.testSuccessful(response.success);
                    if (!response.success && response.hasOwnProperty("msg")) {
                        self.testMessage(response.msg);
                    } else {
                        self.testMessage(undefined);
                    }
                },
                complete: function() {
                    self.testActive(false);
                }
            });
        };

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
        };


    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([LaMetricViewModel, ["loginStateViewModel", "settingsViewModel"], document.getElementById("settings_plugin_lametric")]);
});
