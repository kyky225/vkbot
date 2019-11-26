import dropbox
import json
import vk_api
import pickle
import time
import requests
from vk_api.longpoll import VkLongPoll, VkEventType

def captcha_handler(captcha):
    time.sleep(5)
    main()


class WhiteList:
    def __init__(self, file_name):
        self.__file_name = file_name + '-white-list.dat'
        self.__white_list = self.read_white_list()
        print(self.white_list)

    def read_white_list(self):
        white_list = []
        file = None
        try:
            file = open(self.file_name, 'rb')
            white_list = pickle.load(file)
        except FileNotFoundError as e:
            print(e)
            file = open(self.file_name, 'wb')
            file.close()
        except EOFError as e:
            print(e)
        finally:
            file.close()
            return white_list

    def save_white_list(self):
        file = open(self.file_name, 'wb')
        pickle.dump(self.white_list, file)
        print('White_list successfully was saved')
        file.close()

    def add_id(self, user_id, values):
        if user_id not in self.white_list:
            self.white_list += [user_id]
            values['message'] = 'Пользователь теперь могёт'
        else:
            values['message'] = 'Он уже могёт, что он ещё хочет?'
        self.save_white_list()
        return values

    def delete_id(self, user_id, values):
        if user_id not in self.white_list:
            values['message'] = 'И кого мне удалять?'
        else:
            self.white_list.remove(user_id)
            values['message'] = 'Теперь он не могёт :D'
        self.save_white_list()
        return values

    @property
    def white_list(self):
        return self.__white_list

    @property
    def file_name(self):
        return self.__file_name

    @white_list.setter
    def white_list(self, new_white_list):
        self.__white_list = new_white_list


class Command:
    def __init__(self, file_name):
        self.__file_name = file_name + '.dat'
        self.__commands = self.read_cmd()
        self.white_list = WhiteList(file_name)
        self.__timer = {}

    def create_command(self, text, attachments):
        t = True
        command = {}
        command_text = ''
        command_attachments = ''
        words = str(text).split()
        name = words[1]
        for word in words[2:]:
            command_text += word + ' '
        if attachments is not None:
            attach_type = 'attach1_type'
            attach = 'attach1'
            i = 2
            while attach_type in attachments and attach in attachments:
                command_attachments += attachments[attach_type] + attachments[attach] + ','
                attach_type = 'attach' + str(i) + '_type'
                attach = 'attach' + str(i)
                i += 1
        else:
            command_attachments = ''
        if command_attachments == '' and command_text == '':
            t = False
            return t
        else:
            command[name] = {'text': command_text, 'attach': command_attachments}
        self.commands.update(command)
        self.save_cmd()
        return t

    def upload_dropbox(self):
        dbx = dropbox.Dropbox('')
        f = open(self.file_name, 'rb')
        dbx.files_upload(f.read(), '/test.dat', mode=dropbox.files.WriteMode("overwrite"))
        f.close()

    def invoke(self, event):
        if event.chat_id:
            values = {'chat_id': event.chat_id}
        else:
            values = {'user_id': event.user_id}
        words = str(event.text)
        words = words.split()
        user_id = event.user_id
        if words:
            now_time = time.time()
            if (user_id not in self.timer or now_time - self.timer[user_id] >= 2) and len(words) == 1:
                if words[0] in self.commands:
                        self.timer[user_id] = now_time
                        command_contents = self.commands[words[0]]
                        values['message'] = command_contents['text']
                        values['attachment'] = command_contents['attach']
                        return values
                elif words[0] == '!help':
                    return self.command_help(values)
            elif event.from_me or str(event.user_id) in self.white_list.white_list:
                if words[0] == '!addcmd':
                    return self.add_cmd(words[1], event, values)
                elif words[0] == '!delcmd':
                    return self.delete_cmd(words[1], values)
                elif words[0] == '!editcmd':
                    return self.edit_cmd(words[1], event, values)
                elif event.from_me:
                    if words[0] == '!op':
                        return self.white_list.add_id(words[1], values)
                    elif words[0] == '!deop':
                        return self.white_list.delete_id(words[1], values)

    def add_cmd(self, name, event, values):
        if name in self.commands:
            values['message'] = 'Команда уже существует, попробуй !editcmd'
        else:
            if self.create_command(event.text, event.attachments):
                values['message'] = 'Команда ' + str(name) + ' успешно добавлена'
            else:
                values['message'] = 'Что-то пошло не так'
        return values

    def command_help(self, values):
        commands = 'Список команд:\n'
        for key in self.commands:
            commands += str(key) + '\n'
        values['message'] = commands
        return values

    def delete_cmd(self, name, values):
        if name in self.commands:
            del self.commands[name]
            self.save_cmd()
            values['message'] = 'Команда ' + name + ' успешно удалена.'
        else:
            values['message'] = 'Нету такой команды, чекни !help'
        return values

    def edit_cmd(self, name, event, values):
        if name in self.commands:
            if self.create_command(event.text, event.attachments):
                values['message'] = 'Команда успешно изменена.'
            else:
                values['message'] = 'Something went wrong.'
        else:
            values['message'] = 'Нету такой команды.'
        return values

    def read_cmd(self):
        cmd_list = {}
        try:
            file = open(self.file_name, 'rb')
        except FileNotFoundError as e:
            print(e)
            file = open(self.file_name, 'wb')
            file.close()
            return
        try:
            cmd_list = pickle.load(file)
        except EOFError:
            print('Файл пустой')
        print(cmd_list)
        file.close()
        return cmd_list

    def save_cmd(self):
        file = open(self.file_name, 'wb')
        pickle.dump(self.commands, file)
        file.close()
        self.upload_dropbox()

    @property
    def file_name(self):
        return self.__file_name

    @property
    def commands(self):
        return self.__commands

    @property
    def timer(self):
        return self.__timer

    @commands.setter
    def commands(self, new_cmd):
        self.__commands = new_cmd

    @timer.setter
    def timer(self, new_user_time):
        self.__timer[new_user_time] = time.time()


class Bot:
    def __init__(self, login, password, file_name):
        self.command = Command(file_name)
        self.vk_session = vk_api.VkApi(login, password, captcha_handler=captcha_handler)
        try:
            self.vk_session.auth()
        except vk_api.AuthError as error_msg:
            print(error_msg)
            main()
        self.longPoll = VkLongPoll(self.vk_session)

    def events_check(self):
        for event in self.longPoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                msg = self.command.invoke(event)
                if msg is not None:
                    self.write_msg(msg)

    def write_msg(self, values):
        try:
            self.vk_session.method('messages.send', values)
        except vk_api.ApiError as e:
            print(e)


def main():
    try:
        bot1 = Bot('', '', '')
        bot1.events_check()
    except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
        print('Ошибка соединения\n')
    except json.decoder.JSONDecodeError:
        print('Json error')
    finally:
        main()


if __name__ == '__main__':
    main()
