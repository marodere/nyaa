#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import os, sys, tempfile, subprocess, grp
import urllib, urllib2
import re
import json
import feedparser

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from smtplib import SMTP

def download_url(url):
	httpResponse = urllib2.urlopen(url)
	assert httpResponse.getcode() == 200, "HTTP request %s failed: %d\n" % (url, httpResponse.getcode())
	page = httpResponse.read()
	return page

class TorrentApi:
        @staticmethod
        def download(torrent_data, download_dir, transmission_config):
                download_path = os.path.join(transmission_config["base_download_path"], download_dir)
                if not os.path.isdir(download_path):
                        os.mkdir(download_path)
                        os.chmod(download_path, 0775)
                        os.chown(download_path, -1, grp.getgrnam('transmission').gr_gid)

                tmpfile = tempfile.NamedTemporaryFile(suffix=".torrent")
                tmpfile.write(torrent_data)
                tmpfile.flush()
                sys.stderr.write("Downloading torrent %s to %s\n" % (tmpfile.name, download_path))
                subprocess.check_call(["transmission-remote",
                        transmission_config["api"], "-a",
                        tmpfile.name,
                        "-w",
                        download_path,
                        "-n",
                        "%s:%s" % (transmission_config["user"], transmission_config["password"])])
                tmpfile.close()

class EmailNotifier:
        msg = None
        header = ""
        entries = None
        sig = "Enjoy it.\n\n-- \nsincerely yours\nAnime Notifiction Daemon"

        def __init__(self, series, recipients):
                self.entries = []
                self.recipients = recipients
                self.msg = MIMEMultipart()
                self.msg['Subject'] = '[ongoing] %s episode released' % series["title"]
                self.msg["From"] = 'Anime Notifiction Daemon <noreply@master.onotole.local>'
                self.msg["To"] = ', '.join(self.recipients)
		self.header = "Hi,\n%s new episode(s) released and had to be downloaded." % series["title"]

        def add_entry(self, link, title):
                self.entries.insert(0, "%s is here: %s" % (title, link))

        def submit(self):
                self.msg.attach(MIMEText(self.header + "\n\n"  + "\n".join(self.entries) + "\n\n" + self.sig))
                smtp = SMTP('localhost')
                smtp.sendmail(self.msg['From'], self.recipients, self.msg.as_string())
                smtp.quit()

class FeedProcessor:
        base_url = "http://www.nyaa.se/?page=rss&term=%s"
        feed_url = ""
        regex_pattern = ""
        start_tid = 0
        last_tid = 0

        def __init__(self, fansub_groups, series):
                sys.stderr.write("=== new feed processor ===\n")
                fansub_group = fansub_groups[series["fansub_group"]] if series["fansub_group"] in fansub_groups else fansub_groups["default"]
                self.feed_url = self.base_url % urllib.quote(fansub_group["search_pattern"] % (series["fansub_group"], series["title"]))
                self.regex_pattern = re.compile(fansub_group["regex_pattern"] % (series["fansub_group"]))
                self.start_tid = series["start_tid"] if "start_tid" in series else 0
                self.last_tid = self.start_tid
                sys.stderr.write("looking for title %s fansub_group %s starting from tid %d\n" % (series["title"], series["fansub_group"], self.last_tid))
                sys.stderr.write("rss feed is %s\n" % self.feed_url)

        def get_new_series(self):
                feed = feedparser.parse(self.feed_url)
                tid_pattern = re.compile("[\d]+$")
                for item in feed.entries:
                        current_tid = int(tid_pattern.search(item.link).group(0))
                        if current_tid > self.start_tid and self.regex_pattern.search(item.title):
                                self.last_tid = max(self.last_tid, current_tid)
                                sys.stderr.write("cool, found new episode: %s (%s)\n" % (item.title, item.link))
                                yield (item.link, item.title)

        def get_last_tid(self):
                return self.last_tid

class ActRunner:
        config = None
	config_file = "/home/tolich/anime-fetch/nyaa.json"

        def update(self):
                for series in self.config["series"]:
                        f = FeedProcessor(self.config["fansub_groups"], series)
                        e = EmailNotifier(series, self.config["recipients"])
                        for (torrent_link, torrent_title) in f.get_new_series():
                                e.add_entry(torrent_link, torrent_title)
                                TorrentApi.download(download_url(torrent_link), series["title"], self.config["transmission"])
                        if series["start_tid"] != f.get_last_tid():
                                series["start_tid"] = f.get_last_tid()
                                e.submit()
                        else:
                                sys.stderr.write("sorry, no new episodes found\n")

	def read_config(self):
		try:
			config_fd = open(self.config_file, 'r')
			self.config = json.load(config_fd)
			config_fd.close()
		except:
			sys.stderr.write("Invalid or missed config\n")
                        sys.exit(2)
	
	def write_config(self):
		config_fd = open(self.config_file, 'w')
		json.dump(self.config, config_fd, indent=4)
		config_fd.close()

	def __init__(self):
		self.read_config()
                self.update()
		self.write_config()

def main():
        runner = ActRunner()
        return 0
	

if __name__ == "__main__":
        main()
