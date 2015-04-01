#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  hostsutil.py: Start a TUI session of `Hosts Setup Utility`.
#
# Copyleft (C) 2014 - huhamhire <me@huhamhire.com>
# =====================================================================
# Licensed under the GNU General Public License, version 3. You should
# have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
# =====================================================================

__author__ = "huhamhire <me@huhamhire.com>"
__modifier__ = "kayw"

import os
import sys
import json
import shutil
import socket
import urllib

from zipfile import BadZipfile

from util import CommonUtil, RetrieveData, MakeHosts

class FetchUpdate(object):
    """
    FetchUpdate class contains methods to retrieve the latest hosts data file
    from the project server.

    :ivar str url: The URL of the latest hosts data file.
    :ivar str path: Destination path to save the data file downloaded.
    :ivar str tmp_path: Temporary path to save the data file while
        downloading.
    :ivar int file_size: Size of the data file in bytes.
    :ivar CursesDaemon parent: An instance of
        :class:`~tui.curses_d.CursesDaemon` class to get configuration with.
    """

    def __init__(self, parent):
        """
        Initialize a new instance of this class

        :param parent: An instance of :class:`~tui.curses_d.CursesDaemon`
            class to get configuration with.
        :type parent: :class:`~tui.curses_d.CursesDaemon`
        """
        mirror_id = parent.settings[0][1]
        mirror = parent.mirror
        self.url = mirror["update"] + parent.filename
        self.path = "./" + parent.filename
        self.tmp_path = self.path + ".download"
        self.file_size = parent._update["size"]
        self.parent = parent

    def get_file(self):
        """
        Fetch the latest hosts data file from project server.
        """
        socket.setdefaulttimeout(15)
        try:
            urllib.urlretrieve(self.url, self.tmp_path)
            self.replace_old()
        except Exception, e:
            raise e

    def replace_old(self):
        """
        Replace the old hosts data file with the new one.
        """
        if os.path.isfile(self.path):
            os.remove(self.path)
        os.rename(self.tmp_path, self.path)

class CursesDaemon(object):
    """
    CursesDaemon class contains methods to deal with the operations related to
    `Hosts Setup Utility`.

    :ivar dict _update: Update information of the current data file on server.
    :ivar int _writable: Indicating whether the program is run with admin/root
        privileges. The value could be `1` or `0`.

        .. seealso:: `_update` and `_writable` in
            :class:`~gui.qdialog_d.QDialogDaemon` class.

    :ivar dict make_cfg: A set of module selection control bytes used to
        control whether a specified method is used or not while generate a
        hosts file.

        * `Keys` of :attr:`make_cfg` are typically 8-bit control byte
          indicating which part of the hosts data file would be effected by
          the corresponding `Value`.

          +----+----------------+
          |Key |Part            |
          +====+================+
          |0x02|Localhost       |
          +----+----------------+
          |0x08|Shared hosts    |
          +----+----------------+
          |0x10|IPv4 hosts      |
          +----+----------------+
          |0x20|IPv6 hosts      |
          +----+----------------+
          |0x40|AD block hosts  |
          +----+----------------+

        * `Values` of :attr:`make_cfg` are typically 16-bit control bytes that
          decides which of the modules in a specified part would be inserted
          into the `hosts` file.

            * `Value` of `Localhost` part. The Value used in `Localhost` part
              are usually bytes indicating the current operating system.

              +---------------+-------------------+
              |Hex            |OS                 |
              +===============+===================+
              |0x0001         |Windows            |
              +---------------+-------------------+
              |0x0002         |Linux, Unix        |
              +---------------+-------------------+
              |0x0004         |Mac OS X           |
              +---------------+-------------------+

            * `Values` of `Shared hosts`, `IPv4 hosts`, `IPv6 hosts`, and
              `AD block hosts` parts are usually sum of module IDs selected
              by user.

              .. note::
                If modules in specified part whose IDs are `0x0002` and
                `0x0010`, the value here should be `0x0002 + 0x0010 = 0x0012`,
                which is `0b0000000000000010 + 0b0000000000010000 =
                0b0000000000010010` in binary.

              .. warning::
                Only one bit could be `1` in the binary form of a module ID,
                which means `0b0000000000010010` is an INVALID module ID while
                it could be a VALID `Value` in `make_cfg`.

    :ivar str platform: Platform of current operating system. The value could
        be `Windows`, `Linux`, `Unix`, `OS X`, and of course `Unknown`.
    :ivar str hostname: The hostname of current operating system.

        .. note:: This attribute would only be used on linux.

    :ivar str hosts_path: The absolute path to the hosts file on current
        operating system.
    :ivar str make_mode: Operation mode for making hosts file. The valid value
        could be one of `system`, `ansi`, and `utf-8`.

        .. seealso:: :attr:`make_mode` in
            :class:`~util.makehosts.MakeHosts` class.

    :ivar str make_path: Temporary path to store generated hosts file. The
        default value of :attr:`make_path` is "`./hosts`".
    :ivar list _ops_keys: Hot keys used to start a specified operation.
        Default operation keys are `F5`, `F6`, and `F10`.
    :ivar list _hot_keys: Hot keys used to select a item or confirm an
        operation. And the default :attr:`_hot_keys` is defined as::

            _hot_keys = [curses.KEY_UP, curses.KEY_DOWN, 10, 32]

        .. seealso:: :attr:`~tui.curses_ui.CursesUI.funckeys` in
            :class:`~tui.curses_ui.CursesUI` class.
    :ivar int _item_sup: Upper bound of item index from `function selection
        list`.
    :ivar int _item_inf: Lower bound of item index from `function selection
        list`.
    :ivar str _make_path: Temporary path to store the hosts file in while
        building. The default _make_path is `./hosts`.
    :ivar list _funcs: Two lists with the information of function list both
        for IPv4 and IPv6 environment.
    :ivar list choice: Two lists with the selection of functions both
        for IPv4 and IPv6 environment.
    :ivar list slices: Two lists with integers indicating the number of
        function items from different parts listed in the function list.

    :ivar str sys_eol: The End-Of-Line marker. This maker could typically be
        one of `CR`, `LF`, or `CRLF`.

    :ivar list settings: Two list containing the server selection and IP
        protocol version of current session.

        The settings should be like::

            settings = [["Server", 0, []],
                        ["IP Version", 0, ["IPv4", "IPv6"]]]

    :ivar list funckeys: Lists of hot keys with their function to be shown on
        TUI.

        The default :attr:`funckeys` is defined as::

            funckeys = [["", "Select Item"], ["Tab", "Select Field"],
                        ["Enter", "Set Item"], ["F5", "Check Update"],
                        ["F6", "Fetch Update"], ["F10", "Apply Changes"],
                        ["Esc", "Exit"]]

    :ivar list statusinfo: Two lists containing the connection and OS checking
        status of current session.

        The default :attr:`statusinfo` is defined as::

            statusinfo = [["Connection", "N/A", "GREEN"],
                          ["OS", "N/A", "GREEN"]]

    :ivar dict hostsinfo: Containing the `Version`, `Release Date` of current
        hosts data file and the `Latest Version` of the data file on server.

        The default hostsinfo is defined as::

            hostsinfo = {"Version": "N/A", "Release": "N/A", "Latest": "N/A"}

        .. note:: IF the hosts data file does NOT exist in current working
            directory, OR the file metadata has NOT been checked, the values
            here would just be `N/A`.

    :ivar str filename: Filename of the hosts data file containing data to
        make hosts files from. Default by "`hostslist.data`".
    :ivar str infofile: Filename of the info file containing metadata of the
        hosts data file formatted in JSON. Default by "`hostslist.json`".

        .. seealso:: :attr:`filename` and :attr:`infofile` in
            :class:`~gui.hostsutil.HostsUtil` class.

    :ivar str custom: File name of User Customized Hosts File. Customized
        hosts would be able to select if this file exists. The default file
        name is ``custom.hosts``.

        .. seealso:: :ref:`User Customized Hosts<intro-customize>`.
    """
    _update = {}
    _writable = 0

    make_cfg = {}
    platform = ''
    hostname = ''
    hosts_path = ''

    make_mode = ''
    make_path = "./hosts"

    _item_sup = 0
    _item_inf = 0

    _make_path = "./hosts"
    _funcs = [[], []]
    choice = [[], []]
    slices = [[], []]
    sys_eol = ""

    settings = [["Server", 0, []],
                ["IP Version", 0, ["IPv4", "IPv6"]]]
    funckeys = [["", "Select Item"], ["Tab", "Select Field"],
                ["Enter", "Set Item"], ["F5", "Check Update"],
                ["F6", "Fetch Update"], ["F10", "Apply Changes"],
                ["Esc", "Exit"]]
    statusinfo = [["Connection", "N/A", "GREEN"], ["OS", "N/A", "GREEN"]]
    hostsinfo = {"Version": "N/A", "Release": "N/A", "Latest": "N/A"}

    filename = "hostslist.data"
    infofile = "hostsinfo.json"
    custom = "custom.hosts"
    #_ops_keys = [curses.KEY_F5, curses.KEY_F6, curses.KEY_F10]
    #_hot_keys = [curses.KEY_UP, curses.KEY_DOWN, 10, 32]

    def __init__(self):
        super(CursesDaemon, self).__init__()
        self.check_writable()

    def __del__(self):
        pass

    def check_writable(self):
        """
        Check if current session has write privileges to the hosts file.

        .. note:: IF current session does not has the write privileges to the
            hosts file of current system, a warning message box would popup.

        .. note:: ALL operation would change the `hosts` file on current
            system could only be done while current session has write
            privileges to the file.
        """
        self._writable = CommonUtil.check_privileges()[1]
        if not self._writable:
            print("Please check if you have writing\n"
                            "privileges to the hosts file!")
            #exit()

    def session_daemon(self):
        """
        Operations processed while running a TUI session of `Hosts Setup
        Utility`.

        :return: A flag indicating whether to reload the current session or
            all operations have been finished. The return value could only be
            `0` or `1`. To be specific:

                ====  =========
                flag  operation
                ====  =========
                0     Finish
                1     Reload
                ====  =========

            .. note:: Reload operation is called only when a new data file is
                retrieved from server.

        :rtype: int

        .. note:: IF hosts data file does not exists in current working
            directory, a warning message box would popup. And operations to
            change the hosts file on current system could be done only until
            a new data file has been downloaded.
        """

        key_in = None
        tab = 0
        pos = 0
        tab_entry = [self.configure_settings, self.select_func]
        while key_in != 27:
            for i, sec in enumerate(tab_entry):
                tab_entry[i](pos if i == tab else None)
            if key_in is None:
                test = self.settings[0][2][0]["test_url"]
                self.check_connection(test)
            key_in = screen.getch()
            if key_in == 9:
                if self.choice == [[], []]:
                    tab = 0
                else:
                    tab = not tab
                pos = 0
                """
            elif key_in in self._hot_keys:
                pos = tab_entry[tab](pos, key_in)
            elif key_in in self._ops_keys:
        """
        return 0

    def configure_settings(self, pos=None, key_in=None):
        """
        Perform operations to config settings if `Configure Setting` frame is
        active, or just draw the `Configure Setting` frame with no items
        selected while it is inactive.

        .. note:: Whether the `Configure Setting` frame is inactive is decided
            by if :attr:`pos` is `None` or not.

                ===========  ========
                :attr:`pos`  Status
                ===========  ========
                None         Inactive
                int          Active
                ===========  ========

        :param pos: Index of selected item in `Configure Setting` frame. The
            default value of `pos` is `None`.
        :type pos: int or None
        :param key_in: A flag indicating the key pressed by user. The default
            value of `key_in` is `None`.
        :type key_in: int or None
        :return: Index of selected item in `Configure Setting` frame.
        :rtype: int or None
        """
        id_num = range(len(self.settings))
        if pos is not None:
            if key_in == curses.KEY_DOWN:
                pos = list(id_num[1:] + id_num[:1])[pos]
            elif key_in == curses.KEY_UP:
                pos = list(id_num[-1:] + id_num[:-1])[pos]
            elif key_in in [10, 32]:
                self.sub_selection(pos)
        #     self.info(pos, 0)
        #self.configure_settings_frame(pos)
        return pos

    def select_func(self, pos=None, key_in=None):
        """
        Perform operations if `function selection list` is active, or just
        draw the `function selection list` with no items selected while it is
        inactive.

        .. note:: Whether the `function selection list` is inactive is decided
            by if :attr:`pos` is `None` or not.

        .. seealso:: :meth:`~tui.curses_d.CursesDaemon.configure_settings`.

        :param pos: Index of selected item in `function selection list`. The
            default value of `pos` is `None`.
        :type pos: int or None
        :param key_in: A flag indicating the key pressed by user. The default
            value of `key_in` is `None`.
        :type key_in: int or None
        :return: Index of selected item in `function selection list`.
        :rtype: int or None
        """
        list_height = 15
        ip = self.settings[1][1]
        # Key Press Operations
        item_len = len(self.choice[ip])
        item_sup, item_inf = self._item_sup, self._item_inf
        if pos is not None:
            if item_len > list_height:
                if pos <= 1:
                    item_sup = 0
                    item_inf = list_height - 1
                elif pos >= item_len - 2:
                    item_sup = item_len - list_height + 1
                    item_inf = item_len
            else:
                item_sup = 0
                item_inf = item_len
            if key_in == curses.KEY_DOWN:
                pos += 1
                if pos >= item_len:
                    pos = 0
                if pos not in range(item_sup, item_inf):
                    item_sup += 2 if item_sup == 0 else 1
                    item_inf += 1
            elif key_in == curses.KEY_UP:
                pos -= 1
                if pos < 0:
                    pos = item_len - 1
                if pos not in range(item_sup, item_inf):
                    item_inf -= 2 if item_inf == item_len else 1
                    item_sup -= 1
            elif key_in in [10, 32]:
                self._funcs[ip][pos] = not self._funcs[ip][pos]
                mutex = RetrieveData.get_ids(self.choice[ip][pos][2])
                for c_id, c in enumerate(self.choice[ip]):
                    if c[0] == self.choice[ip][pos][0]:
                        if c[1] in mutex and self._funcs[ip][c_id] == 1:
                            self._funcs[ip][c_id] = 0
            self.info(pos, 1)
        else:
            item_sup = 0
            if item_len > list_height:
                item_inf = list_height - 1
            else:
                item_inf = item_len
        self.show_funclist(pos, item_sup, item_inf)
        return pos

    def sub_selection(self, pos):
        """
        Let user to choose settings from `Selection Dialog` specified by
        :attr:`pos`.

        :param pos: Index of selected item in `Configure Setting` frame.
        :type pos: int

        .. warning:: The value of `pos` MUST NOT be `None`.

        .. seealso:: :meth:`~tui.curses_ui.CursesUI.sub_selection_dialog` in
            :class:`~tui.curses_ui.CursesUI`.
        """
        screen = self.sub_selection_dialog(pos)
        i_pos = self.settings[pos][1]
        # Key Press Operations
        id_num = range(len(self.settings[pos][2]))
        key_in = None
        while key_in != 27:
            self.sub_selection_dialog_items(pos, i_pos, screen)
            key_in = screen.getch()
            if key_in == curses.KEY_DOWN:
                i_pos = list(id_num[1:] + id_num[:1])[i_pos]
            elif key_in == curses.KEY_UP:
                i_pos = list(id_num[-1:] + id_num[:-1])[i_pos]
            elif key_in in [10, 32]:
                if pos == 0 and i_pos != self.settings[pos][1]:
                    test = self.settings[pos][2][i_pos]["test_url"]
                    self.check_connection(test)
                self.settings[pos][1] = i_pos
                return

    def check_connection(self, url):
        """
        Check connection status to the server currently  selected by user and
        show a status box indicating current operation.

        :param url: The link of the server chose by user.This string could be
            a domain name or the IP address of a server.

            .. seealso:: :attr:`link` in
                :meth:`~util.common.CommonUtil.check_connection`.
        :type url: str
        :return: A flag indicating connection status is good or not.

            .. seealso:: :meth:`~util.common.CommonUtil.check_connection`. in
                :class:`~util.common.CommonUtil` class.
        :rtype: int
        """
        print("Checking Server Status...")
        conn = CommonUtil.check_connection(url)
        if conn:
            self.statusinfo[0][1] = "OK"
            self.statusinfo[0][2] = "GREEN"
        else:
            self.statusinfo[0][1] = "Error"
            self.statusinfo[0][2] = "RED"
        return conn

    def check_update(self):
        """
        Check the metadata of the latest hosts data file from server and
        show a status box indicating current operation.

        :return: A dictionary containing the `Version`, `Release Date` of
            current hosts data file and the `Latest Version` of the data file
            on server.

            IF error occurs while checking update, the dictionary would be
            defined as::

                {"version": "[Error]"}
        :rtype: dict
        """
        if os.path.isfile(self.infofile):
            with open(self.infofile) as f:
                jsons = f.read()
                info = json.loads(jsons)
                return info

        print("Checking Update...")
        srv_id = self.settings[0][1]
        url = ""#self.settings[0][2][srv_id]["update"] + self.infofile
        for srv_id,server_info in enumerate(self.settings[0][2]):
            url = server_info['test_url']
            print(url)
            if self.check_connection(url):#['test_url']):
                url = server_info['update'] + self.infofile
                self.mirror = server_info
                break
                                            
        try:
            socket.setdefaulttimeout(15)
            url_obj = urllib.urlopen(url)
            j_str = url_obj.read()
            url_obj.close()
            info = json.loads(j_str)
        except Exception,e:
            print("open url %s error:%s".format(url, e))
            info = {"version": "[Error]"}
        self.hostsinfo["Latest"] = info["version"]
        return info

    def new_version(self):
        """
        Compare version of local data file to the version from the server.

        :return: A flag indicating whether the local data file is up-to-date
            or not.

            ======  ============================================
            Return  Data file status
            ======  ============================================
            1       The version of data file on server is newer.
            0       The local data file is up-to-date.
            ======  ============================================
        :rtype: int
        """
        local_ver = self.hostsinfo["Version"]
        if local_ver == "N/A":
            return 1
        server_ver = self._update["version"]
        local_ver = local_ver.split('.')
        server_ver = server_ver.split('.')
        for i, ver_num in enumerate(local_ver):
            if server_ver[i] > ver_num:
                return 1
        return 0

    def fetch_update(self):
        """
        Retrieve the latest hosts data file from server and show a status box
        indicating current operation.
        """
        print("Downloading...")
        fetch_d = FetchUpdate(self)
        fetch_d.get_file()

    def set_config_bytes(self):
        """
        Calculate the module configuration byte words by the selection from
        function list on the main dialog.
        """
        ip_flag = self.settings[1][1]
        selection = {}
        localhost_word = {
            "Windows": 0x0001, "Linux": 0x0002,
            "Unix": 0x0002, "OS X": 0x0004}[self.platform]
        selection[0x02] = localhost_word
        ch_parts = [0x08, 0x20 if ip_flag else 0x10, 0x40]
        # Set customized module if exists
        if os.path.isfile(self.custom):
            ch_parts.insert(0, 0x04)
        slices = self.slices[ip_flag]
        for i, part in enumerate(ch_parts):
            part_cfg = self._funcs[ip_flag][slices[i]:slices[i + 1]]
            part_word = 0
            for i, cfg in enumerate(part_cfg):
                part_word += cfg << i
            selection[part] = part_word
        self.make_cfg = selection

    def move_hosts(self):
        """
        Move hosts file to the system path after making operations are
        finished.
        """
        filepath = "hosts"
        try:
            shutil.copy2(filepath, self.hosts_path)
        except IOError:
            os.remove(filepath)
            return
        os.remove(filepath)
        print("Operation completed!")

class HostsUtil(CursesDaemon):
    """
    HostsUtil class is the main entrance to the
    `Hosts Setup Utility`. 

    .. note:: This class is subclass of :class:`~.CursesDaemon`
        class.

    .. inheritance-diagram:: tui.hostsutil.HostsUtil
        :parts: 2


    :ivar str platform: Platform of current operating system. The value could
        be `Windows`, `Linux`, `Unix`, `OS X`, and of course `Unknown`.
    :ivar str hostname: The hostname of current operating system.

        .. note:: This attribute would only be used on linux.
    :ivar str hosts_path: The absolute path to the hosts file on current
        operating system.

        .. seealso:: :attr:`platform`, :attr:`hostname`, :attr:`hosts_path` in
            :class:`~tui.curses_d.CursesDaemon` class.
    :ivar str sys_eol: The End-Of-Line marker. This maker could typically be
        one of `CR`, `LF`, or `CRLF`.

        .. seealso:: :attr:`sys_eol` in :class:`~tui.curses_ui.CursesUI`
            class.
    """
    platform = ""
    hostname = ""
    hosts_path = ""
    sys_eol = ""

    def __init__(self):
        """
        Initialize a new TUI session.

        * Load server list from a configuration file under working directory.
        * Try to load the hosts data file under working directory if it
          exists.

        .. note:: IF hosts data file does not exists correctly in current
            working directory, a warning message box would popup. And
            operations to change the hosts file on current system could be
            done only until a new data file has been downloaded.

        .. seealso:: :meth:`~tui.curses_d.CursesDaemon.session_daemon` method
            in :class:`~tui.curses_d.CursesDaemon`.

        .. seealso:: :meth:`~gui.hostsutil.HostsUtil.init_main` in
            :class:`~gui.hostsutil.HostsUtil` class.
        """
        super(HostsUtil, self).__init__()
        # Set mirrors
        self.settings[0][2] = CommonUtil.set_network("network.conf")
        # Read data file and set function list
        try:
            self.set_platform()
            if os.path.isfile(self.filename):
                RetrieveData.unpack()
                RetrieveData.connect_db()
                self.set_info()
                self.set_func_list()
            self._update = self.check_update()
            # Check if data file up-to-date
            if self.new_version():
                self.fetch_update()
                """
                TODO: need to be done more elegantly
                """
                RetrieveData.unpack()
                RetrieveData.connect_db()
                self.set_info()
                self.set_func_list()
        except IOError:
            print("No data file found! Press F6 to get data file "
                            "first.")
        except BadZipfile:
            print("Incorrect Data file! Press F6 to get a new data "
                            "file first.")

    def __del__(self):
        """
        Reset the terminal and clear up the temporary data file while TUI
        session is finished.
        """
        super(HostsUtil, self).__del__()
        try:
            RetrieveData.clear()
        except:
            pass

    def start(self):
        """
        Start the host setup session.

        """
        self.set_config_bytes()
        self.make_mode = "system"
        maker = MakeHosts(self)
        maker.make()
        #self.move_hosts()

    def set_platform(self):
        """
        Set the information about current operating system.
        """
        system, hostname, path, encode, flag = CommonUtil.check_platform()
        color = "GREEN" if flag else "RED"
        self.platform = system
        self.statusinfo[1][1] = system
        self.hostname = hostname
        self.hosts_path = path
        self.statusinfo[1][2] = color
        if encode == "win_ansi":
            self.sys_eol = "\r\n"
        else:
            self.sys_eol = "\n"

    def set_func_list(self):
        """
        Set the function selection list in TUI session.
        """
        for ip in range(2):
            choice, defaults, slices = RetrieveData.get_choice(ip)
            if os.path.isfile(self.custom):
                choice.insert(0, [4, 1, 0, "customize"])
                defaults[0x04] = [1]
                for i in range(len(slices)):
                    slices[i] += 1
                slices.insert(0, 0)
            defaults[0x40].append(1) #adblocks-hostsx
            defaults[0x40].append(2) #adblock-mvp
            if 0x10 in defaults:
            #http://stackoverflow.com/questions/4915920/how-to-delete-an-item-in-a-list-if-it-exists-python
                try:
                    defaults[0x10].remove(256) #no github
                    defaults[0x10].remove(32) #no wiki
                except ValueError:
                    pass
            self.choice[ip] = choice
            self.slices[ip] = slices
            funcs = []
            for func in choice:
                if func[1] in defaults[func[0]]:
                    funcs.append(1)
                else:
                    funcs.append(0)
            self._funcs[ip] = funcs

    def set_info(self):
        """
        Set the information of the current local data file.
        """
        info = RetrieveData.get_info()
        build = info["Buildtime"]
        self.hostsinfo["Version"] = info["Version"]
        self.hostsinfo["Release"] = CommonUtil.timestamp_to_date(build)

if __name__ == "__main__":
    main = HostsUtil()
    main.start()
