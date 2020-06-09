# coding=utf-8
from __future__ import absolute_import


import octoprint.plugin
import requests,base64
import json
import urllib3
from octoprint.util import RepeatedTimer
from time import sleep



class LaMetricPlugin(octoprint.plugin.SettingsPlugin,
					octoprint.plugin.AssetPlugin,
					octoprint.plugin.EventHandlerPlugin,
					octoprint.plugin.StartupPlugin,
					octoprint.plugin.ProgressPlugin,
					octoprint.plugin.TemplatePlugin):
	timer = None
	printing = False
	remote_queue = []
	interval = 10

	def on_after_startup(self):
		"""
		Event when octoprint is started
		:return: 
		"""
		self.event_message({
			"frames": [
				{
					"icon": "i37809",
					"text": "OctoPrint"
				}
			]
		})

	def print_done(self, payload):
		"""
		Print is done
		:param payload: 
		:return: 
		"""
		self.event_message({
			"frames": [
				{
					"icon": "i37809",
					"text": "Done"
				}
			]
		})

	def print_failed(self, payload):
		"""
		Print is failed 
		:param payload: 
		:return: 
		"""
		self.event_message({
			"frames": [
				{
					"icon": "13064",
					"text": "Print failed"
				}
			]
		})

		sleep(30)
		self.on_after_startup()

	def print_paused(self, payload):
		"""
		Print is paused
		:param payload: 
		:return: 
		"""
		self.event_message({
			"frames": [
				{
					"icon": "20944",
					"text": "Paused"
				}
			]
		})

	def print_started(self, payload):
		"""
		Reset value's
		:param payload:
		:return:
		"""
		self.restart_timer()

	def on_event(self, event, payload):
		"""
		On event switcher
		:param event: 
		:param payload: 
		:return: 
		"""
		self._logger.debug("Got an event: " + event + " Payload: " + str(payload))

		if event == "PrintStarted":
			self.print_started(payload)
		elif event == "PrintPaused" or event == "PrintPaused":
			self.print_paused(payload)
		elif event == "PrintFailed":
			self.print_failed(payload)
		elif event == "PrintDone":
			self.print_done(payload)

	def stop_timer(self):
		"""
		Stop timer used in track temperature progress
		:return: 
		"""
		self.timer.cancel()
		self.timer = None

	def restart_timer(self):
		"""
		Start/restart timer used in track temperature progress
		:return: 
		"""

		if self.timer:
			self.stop_timer()


		self.timer = RepeatedTimer(self.interval, self.temp_check, None, None, True)
		self.timer.start()

	def temp_check(self):
		"""
		Check temperature
		:return: 
		"""

		if not self._printer.is_operational():
			return

		temps = self._printer.get_current_temperatures()

		bed_temp = round(temps['bed']['actual']) if 'bed' in temps else 0
		bed_target = temps['bed']['target'] if 'bed' in temps else 0
		e1_temp = round(temps['tool0']['actual']) if 'tool0' in temps else 0
		e1_target = temps['tool0']['target'] if 'tool0' in temps else 0

		self.event_message({
			"frames": [
				{
					"icon": "2355",
					"goalData": {
						"start": 0,
						"current": e1_temp,
						"end": e1_target,
						"unit": u'\N{DEGREE SIGN}C'
					}
				},
				{
					"icon": "2355",
					"goalData": {
						"start": 0,
						"current": bed_temp,
						"end": bed_target,
						"unit": u'\N{DEGREE SIGN}C'
					}
				}
			]
		})

		if e1_target > 0 and e1_temp >= e1_target and bed_target > 0 and bed_temp >= bed_target:
			self.stop_timer()

	def on_print_progress(self, storage, path, progress):
		"""
		Event for print progress
		:param storage: 
		:param path: 
		:param progress: 
		:return: 
		"""
		self.event_message({
			"frames": [
				{
					"icon": "i37809",
					"goalData": {
						"start": 0,
						"current": progress,
						"end": 100,
						"unit": "%"
					}
				}
			]
		})

	def event_message(self, frames):
		"""
		Send the message to the device
		:param frames: 
		:return: 
		"""

		if self._settings.get(["host"]) is None:
			return

		if self._settings.get(["key"]) is None:
			return

		url = "https://" + self._settings.get(["host"]) + ":4343/api/v2/device/notifications"

		headers = {
			"Content-Type": "application/json",
			"Cache-Control": "no-cache",
			"Authorization": "Basic %s" % base64.b64encode(b'dev:' + self._settings.get(["key"]).encode()).decode('utf-8')
		}

		model = {
			"priority": "info",
			"icon_type": "none",
			"lifeTime": (self.interval * 1000),
			"model": frames
		}

		# Otherwise every INTERVAL second a warning is written to the log file
		urllib3.disable_warnings()

		# Post, delete, add to the queue. Otherwise the Lametric displays flickers
		# First post the message
		r = requests.post(url, verify=False, data=json.dumps(model), headers=headers)
		# Verify has too be False according too the Lametric documentation :/
		# https://lametric-documentation.readthedocs.io/en/latest/reference-docs/device-discovery.html
		result = json.loads(r.content)

		# Then delete every other notifications
		while self.remote_queue:
			requests.delete(url + "/" + self.remote_queue.pop(0), verify=False, headers=headers)
			# Verify has too be False according too the Lametric documentation :/
			# https://lametric-documentation.readthedocs.io/en/latest/reference-docs/device-discovery.html

		try:
			if(result["success"]["id"] is not None):
				# Add the newly created notification too the queue
				self.remote_queue.append(result["success"]["id"])

		except KeyError:
			pass

		# Or do we get an error
		try:
			message = result["errors"][0]["message"]
			# Filter the "Only notifications with priority 'critical' are allowed in current mode" messages
			if("critical" not in message):
				self._logger.info(message)

		except KeyError:
			pass

	def on_settings_save(self, data):
		"""
		Valide settings onm save
		:param data: 
		:return: 
		"""
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		self.event_message({
			"frames": [
				{
					"icon": "5400",
					"text": "Connected"
				}
			]
		})


	def get_settings_defaults(self):
		"""
		Defaults
		:return: 
		"""
		return dict(
			host =None,
			key=None
		)

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False),
		]

	def get_update_information(self):
		return dict(
			lametric=dict(
				displayName="LaMetric Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="thijsbekke",
				repo="OctoPrint-LaMetric",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/thijsbekke/OctoPrint-LaMetric/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "LaMetric"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = LaMetricPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
