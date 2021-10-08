import grbl_comm

class GrblSender(grbl_comm.GrblComm):

    def __init__(self, port='/dev/ttyACM0', baudrate=115200, timeout=None):
        super().__init__(port=port, baudrate=baudrate, timeout=timeout)
        self.cmd_to_send = []
        self.cmd_in_buff = []
        self.char_counts = []
        self.debug = False

    @property
    def sending(self):
        return self.cmd_to_send or self.cmd_in_buff
        
    def append_cmd(self,cmd):
        self.cmd_to_send.append(f'{cmd}\n')

    def extend_cmd(self, cmd_list):
        for cmd in cmd_list:
            self.append_cmd(cmd)

    def soft_stop(self):
        self.feedhold()
        self.reset()
        self.kill_alarm_lock()
        self.cmd_to_send = []
        self.cmd_in_buff = []
        self.char_counts = []

    def set_zero(self):
        print('set zero')
        self.append_cmd(f'G10P1L20 X0 Y0 Z0')
        self.append_cmd(f'G54')


    def clear_zero(self):
        print('clear zero')
        self.append_cmd(f'G10P1L2 X0 Y0 Z0')
        self.append_cmd(f'G54')

    def update(self, query_status=False): 
        rval = {} 
        if self.debug: 
            if self.cmd_to_send:
                print(f'cmd_to_send: {self.cmd_to_send}')
            if self.cmd_in_buff:
                print(f'cmd_in_buf:  {self.cmd_in_buff}')
                print(f'char_counts: {self.char_counts}')
                print(f'sum(char_counts): {sum(self.char_counts)}')
                print()

        if query_status:
            if not self.cmd_to_send or self.cmd_to_send[-1] != self.CMD_GET_STATUS:
                self.write(f'{self.CMD_GET_STATUS}'.encode())

        if self.cmd_to_send:
            cmd = self.cmd_to_send[0]
            if (sum(self.char_counts) + len(cmd)) < self.RX_BUFFER_SIZE:
                self.write('{}'.format(cmd).encode())
                self.char_counts.append(len(cmd))
                self.cmd_in_buff.append(cmd)
                del self.cmd_to_send[0]

        if self.in_waiting:
            line = self.readline().decode('UTF-8').strip()
            if 'ok' in line or 'error' in line:
                del self.cmd_in_buff[0]
                del self.char_counts[0]
                
            elif 'MPos' in line or 'WPos' in line:
                status = grbl_comm.extract_status_from_line(line)
                rval['status'] = status

        return rval





