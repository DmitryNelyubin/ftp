from ftplib import FTP
from zipfile import ZipFile
from datetime import datetime
from tqdm import tqdm
import xml.etree.ElementTree as ET
import os
import shutil
import sys


class FtpConnect:
    def __init__(self):
        self.__ftp = FTP('ftp.zakupki.gov.ru')
        self.__ftp_path = '/fcs_regions/'
        self.__file_names_exceptions = ["PG-PZ", "ERUZ"]
        self.__periods = ["currMonth", "prevMonth", ""]

        self.__file_names = []

        self.__path = f'{os.getcwd()}/ftp-data/'
        self.__notification_number_path = f'{self.__path}find-by-number/'
        self.__path_zip = f'{self.__path}data-zip/'
        self.__path_unzip = f'{self.__path}data-unzip/'
        self.__f_out = open("XML-data.txt", "w")

    def connect(self):
        self.__ftp.login("free", "free")
        self.__ftp.cwd(self.__ftp_path)

        self.__file_names = self.__ftp.nlst()
        self.__file_names = self.__file_names[self.__file_names.index(
            'Adygeja_Resp'):self.__file_names.index('Zabajkalskij_kraj') + 1]
        for i in self.__file_names_exceptions:
            self.__file_names.remove(i)

        self.menu()

    def menu(self):
        if not os.path.exists(self.__path):
            os.makedirs(self.__path)
        else:
            shutil.rmtree(self.__path)
            os.makedirs(self.__path)

        print("1. Monitoring\n2. Find by date or by number")
        choice_menu = self.check_input(2)
        if choice_menu == 1:
            self.monitoring()
        else:
            self.find_date_or_number()

        self.__f_out.close()
        self.__ftp.quit()

        print("\nDone!\n")
        input("Press Enter to exit . . .")

    def monitoring(self):
        data = f'{self.check_month_or_day(31)}'
        prev_count = 0
        count_unzip_files = 0
        for region in self.__file_names:
            monitoring_path = f'{self.__ftp_path}' \
                              f'{region}/notifications/currMonth/'
            self.__ftp.cwd(monitoring_path)
            self.__file_names = self.__ftp.nlst()

            self.find_by_day(data)
            self.download_notifications()

            files = os.listdir(self.__path_unzip)

            count_unzip_files = 0
            for file in files:
                if not ("cancel" in file.lower() or ".sig" in file.lower()
                        or "notification" not in file.lower()):
                    count_unzip_files += 1
            print(count_unzip_files - prev_count, "in", region)
            prev_count = count_unzip_files

        print("Total", count_unzip_files, "files")
        self.parse_xml()

    def find_date_or_number(self):
        for i in range(len(self.__file_names)):
            print(i + 1, self.__file_names[i])

        region_choice = self.check_input(len(self.__file_names)) - 1
        self.__ftp_path = f'{self.__ftp_path}' \
                          f'{self.__file_names[region_choice]}/notifications/'

        print("1. Find by date\n2. Find by number")
        choice_menu = self.check_input(2)
        if choice_menu == 1:
            self.find_by_date()
        else:
            self.find_by_number()

    def find_by_date(self):
        print("Choose period:\n1. Current month\n"
              "2. Previous month\n3. Choose date")
        period_choice = self.check_input(len(self.__periods)) - 1
        self.__ftp_path = f'{self.__ftp_path}{self.__periods[period_choice]}'

        self.__ftp.cwd(self.__ftp_path)
        self.__file_names = self.__ftp.nlst()
        if period_choice == 2:
            self.find_by_date_other_period(1)

        self.download_notifications()

        print("")
        self.parse_xml()

    def find_by_number(self):
        if not os.path.exists(self.__notification_number_path):
            os.makedirs(self.__notification_number_path)

        number = self.check_notification_number()
        reversed_periods = self.__periods[::-1]
        for period in reversed_periods:
            ftp_search_path = f'{self.__ftp_path}{period}'
            self.__ftp.cwd(ftp_search_path)
            self.__file_names = self.__ftp.nlst()
            if period == "":
                self.find_by_date_other_period(2)

            self.download_notifications()

        files = os.listdir(self.__path_unzip)
        found_count = 0
        print("")
        print("Searching...")
        for file in tqdm(files):
            curr_number = file.split('_')[1]
            if number == curr_number and ".sig" not in file.lower():
                found_count += 1
                shutil.copy(f'{self.__path_unzip}{file}',
                            self.__notification_number_path)
        print("", end="", flush=True)

        if found_count > 0:
            print(f'{found_count} files were found')
        else:
            print("No files were found")

    def find_by_day(self, data):
        file_names_by_data = []

        for file in self.__file_names:
            split = file.split("_")
            index = 1
            for j in range(len(split)):
                if split[j][0].isdigit():
                    index = j
                    break
            if data == split[index][6:8]:
                file_names_by_data.append(file)
        if len(file_names_by_data) == 0:
            print("No files found in that day")
            input("Press Enter to exit . . .")
            sys.exit()
        else:
            self.__file_names = file_names_by_data

    def find_by_date_other_period(self, flag: int):
        self.__file_names.remove("prevMonth")
        self.__file_names.remove("currMonth")
        print("Find by date")
        while True:
            file_names_by_data = []
            data = f'{self.check_year()}{self.check_month_or_day()}'

            for file in self.__file_names:
                split = file.split("_")
                index = 1
                for j in range(len(split)):
                    if split[j][0].isdigit():
                        index = j
                        break
                if data in split[index]:
                    file_names_by_data.append(file)
            if flag != 1:
                self.__file_names = file_names_by_data
                return
            if len(file_names_by_data) == 0:
                print("No files found by the given date")
                print("1. Try another date\n2. Exit")
                if self.check_input(2) == 1:
                    continue
                else:
                    sys.exit()
            else:
                self.__file_names = file_names_by_data
                break

        return data

    def download_notifications(self):
        if not os.path.exists(self.__path_zip):
            os.makedirs(self.__path_zip)

        if not os.path.exists(self.__path_unzip):
            os.makedirs(self.__path_unzip)

        print("", end="", flush=True)
        print("Unpacking:")
        for file in tqdm(self.__file_names):
            with open(f'{self.__path_zip}{file}', "wb") as f:
                self.__ftp.retrbinary(f'RETR {file}', f.write)
            with ZipFile(f'{self.__path_zip}{file}', 'r') as f:
                f.extractall(f'{self.__path_unzip}')
        print("", end="", flush=True)
        shutil.rmtree(self.__path_zip)

    def parse_xml(self):
        files = os.listdir(self.__path_unzip)

        print("", end="", flush=True)
        print("Parsing xml . . .")
        for file_ in tqdm(files):
            if "cancel" in file_.lower() or \
                    ".sig" in file_.lower() or \
                    "notification" not in file_.lower():
                continue

            ind = file_.lower().split("_")[0].find("notification") + \
                  len("notification")

            self.__f_out.write(f'{file_.lower().split("_")[0][ind:]} ')

            if file_.lower()[:3] == "fks" or file_.lower()[:3] == "fcs":
                self.parse_xml_fks(file_)
            else:
                self.parse_xml_ep(file_)
        print("", end="", flush=True)

    def parse_xml_fks(self, file_):
        tree = ET.parse(
            f'{self.__path_unzip}{file_}')
        root = tree.getroot()

        z = self.find_node(root, "purchaseNumber")
        try:
            self.__f_out.write(f'{z.text} ')
        except AttributeError:
            print(f'{self.__path_unzip}{file_} has no purchaseNumber')

        z = self.find_node(root, "docPublishDate")
        try:
            self.__f_out.write(f'{z.text} ')
        except AttributeError:
            print(f'{self.__path_unzip}{file_} has no docPublishDate, '
                  f'trying publishDTInEIS instead')
            z = self.find_node(root, "publishDTInEIS")
            try:
                self.__f_out.write(f'{z.text} ')
            except AttributeError:
                print(f'{self.__path_unzip}{file_} '
                      f'has no publishDTInEIS also')

        z = root[0].find("{*}ETP")
        if z is not None:
            zz = z.find("{*}code")
            self.__f_out.write(f'{zz.text} ')
        else:
            print(f'{self.__path_unzip}{file_} has no ETP')
        self.__f_out.write("\n")

    def parse_xml_ep(self, file_):
        tree = ET.parse(
            f'{self.__path_unzip}{file_}')
        root = tree.getroot()

        z = root[0].find("{*}commonInfo")
        try:
            zz = z.find("{*}purchaseNumber")
        except AttributeError:
            print(f'{self.__path_unzip}{file_}')
        try:
            self.__f_out.write(f'{zz.text} ')
        except AttributeError:
            print(f'{self.__path_unzip}{file_} has no purchaseNumber')

        zz = z.find("{*}publishDTInEIS")
        self.__f_out.write(f'{zz.text} ')

        zz = z.find("{*}ETP")
        zzz = zz.find("{*}code")
        self.__f_out.write(f'{zzz.text} ')

        z = root[0].find("{*}versionNumber")
        try:
            self.__f_out.write(f'{z.text}\n')
        except AttributeError:
            print(f'{self.__path_unzip}{file_} has no versionNumber')

    @staticmethod
    def check_input(range_check: int):
        while True:
            try:
                n = int(input(f'Choose the option(1-{range_check}):'))
                if 1 <= n <= range_check:
                    return n
                else:
                    raise ValueError
            except ValueError:
                print("Incorrect input! \nTry again")

    @staticmethod
    def check_notification_number():
        while True:
            try:
                number = input("Enter notification number:")
                if len(number) != 19:
                    raise ValueError
                for i in number:
                    if not i.isdigit():
                        raise ValueError
                return number
            except ValueError:
                print("Incorrect format\nTry again")

    @staticmethod
    def check_year():
        max_year = datetime.now().year
        while True:
            try:
                year = int(input(f'Enter the year:'))
                if 9 < year < 100:
                    year += 2000
                if max_year < year or year < 2014:
                    raise ValueError
                return f'{year}'
            except ValueError:
                print("Incorrect input! Check your system date\nTry again")

    @staticmethod
    def check_month_or_day(option=12):
        search_string = "month" if option == 12 else "day"
        while True:
            try:
                number = int(input(f'Enter the {search_string}(1-{option}):'))
                if option < number or number < 1:
                    raise ValueError
                if number < 10:
                    number = f'0{number}'
                return f'{number}'
            except ValueError:
                print("Incorrect input!\nTry again")

    @staticmethod
    def find_node(root_, s: str):
        for node in root_.iter():
            if s in node.tag:
                return node
        return None


if __name__ == "__main__":
    ftp_conn = FtpConnect()
    ftp_conn.connect()
