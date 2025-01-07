import socket
import threading
import tkinter as tk
from tkinter import simpledialog, colorchooser, messagebox
import pickle
import random
import string


BUFFER_SIZE = 8192    # Size of the buffer for receiving data 
BROADCAST_PORT = 37020  # Port for broadcasting room codes
DRAW = "DRAW"  # Message type for drawing actions
CLEAR = "CLEAR"  # Message type for clearing the canvas
PEER = "PEER"  # Message type for peer information
MAP = "MAP"  # Message type for broadcasting room maps


# Generate random room code
def generate_room_code(length = 6) :
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# Whiteboard GUI Class
class Whiteboard:
    def __init__(self, master, ip, port, user_name, is_host = False, room_code = None): # Initialize the Whiteboard

        self.master = master  # Reference to the main Tkinter window
        self.master.title("Peer-to-Peer Whiteboard")  # Set the window title

        # Room Code Label (if host)
        if is_host and room_code:
            self.room_label = tk.Label(self.master, text=f"Room Code: {room_code}", font=("Arial", 14))  # Create a label displaying the room code with Arial font size 14
            self.room_label.pack(pady=5) # Place the label in the window with 5 pixels padding on the y-axis

        # Canvas
        self.canvas = tk.Canvas(self.master, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)

      
        # Toolbar
        screen_height = self.master.winfo_screenheight()  
        toolbar_height = int(screen_height * 0.05)  
        self.toolbar = tk.Canvas(self.master, height=toolbar_height)  
        self.toolbar.pack(fill=tk.X)  


        self.color_button = tk.Button(self.toolbar, text="Color", command=self.choose_color, bg="lightblue", fg="black", font=("Comic Sans MS", 10, "bold"), relief=tk.RAISED, bd=2) 
        self.color_button.pack(side=tk.LEFT, padx=5, pady=5) 

        # Add hover effect to change the button color and cursor
        def on_enter(e):
            self.color_button['background'] = 'deepskyblue'
            self.color_button['cursor'] = 'hand2'

        def on_leave(e):
            self.color_button['background'] = 'lightblue'
            self.color_button['cursor'] = ''

        self.color_button.bind("<Enter>", on_enter)
        self.color_button.bind("<Leave>", on_leave)

        self.bg_color_button = tk.Button(self.toolbar, text="Background Color", command=self.choose_bg_color, bg="lightblue", fg="black", font=("Comic Sans MS", 10, "bold"), relief=tk.RAISED, bd=2) 
        self.bg_color_button.pack(side=tk.LEFT, padx=5, pady=5) 

        def on_enter_bg(e):
            self.bg_color_button['background'] = 'deepskyblue'
            self.bg_color_button['cursor'] = 'hand2'

        def on_leave_bg(e):
            self.bg_color_button['background'] = 'lightblue'
            self.bg_color_button['cursor'] = ''

        self.bg_color_button.bind("<Enter>", on_enter_bg)
        self.bg_color_button.bind("<Leave>", on_leave_bg)

        self.size_label = tk.Label(self.toolbar, text="Brush Size:", font=("Comic Sans MS", 10, "bold")) # Create a label for the brush size
        self.size_label.pack(side=tk.LEFT, padx=5)

        self.size_slider = tk.Scale(self.toolbar, from_=1, to=10, orient=tk.HORIZONTAL, bg="lightblue", fg="black", font=("Comic Sans MS", 10, "bold"), relief=tk.RAISED, bd=2)
        self.size_slider.set(2)
        self.size_slider.pack(side=tk.LEFT, padx=5)

        def on_enter_slider(e):
            self.size_slider['background'] = 'deepskyblue'
            self.size_slider['cursor'] = 'hand2'

        def on_leave_slider(e):
            self.size_slider['background'] = 'lightblue'
            self.size_slider['cursor'] = ''

        self.size_slider.bind("<Enter>", on_enter_slider)
        self.size_slider.bind("<Leave>", on_leave_slider)

        self.clear_button = tk.Button(self.toolbar, text="Clear", command=self.clear_canvas, bg="lightblue", fg="black", font=("Comic Sans MS", 10, "bold"), relief=tk.RAISED, bd=2) # Create a styled button to clear the canvas
        self.clear_button.pack(side=tk.LEFT, padx=5)

        def on_enter_clear(e):
            self.clear_button['background'] = 'deepskyblue'
            self.clear_button['cursor'] = 'hand2'

        def on_leave_clear(e):
            self.clear_button['background'] = 'lightblue'
            self.clear_button['cursor'] = ''

        self.clear_button.bind("<Enter>", on_enter_clear)
        self.clear_button.bind("<Leave>", on_leave_clear)

        

        self.peers_label = tk.Label(self.toolbar, text="Connected Peers:", font=("Comic Sans MS", 10, "bold"))
        self.peers_label.pack(side=tk.LEFT, padx=10)

        self.peers_list = tk.Listbox(self.toolbar, height=3, width=30, bg="lightblue", fg="black", font=("Comic Sans MS", 10, "bold"), relief=tk.RAISED, bd=2)
        self.peers_list.pack(side=tk.LEFT, padx=5)

        # Variables for drawing
        self.old_x = None
        self.old_y = None
        self.brush_color = 'black'
        self.brush_size = 2

        # Networking
        self.ip = ip                                                    # IP address of the host
        self.port = port                                                # Port number for the host
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # Create a TCP socket for the host with ipv4
        self.peers = []                                                 # List of connected peers
        self.peer_map = {}                                              # Dictionary of peer names and addresses
        self.user_name = user_name                                      # Name of the user      

        # Start server thread
        threading.Thread(target=self.start_server, daemon=True).start()     # Start the server thread in the background

        # Broadcast room code if host
        if is_host and room_code:
            self.room_code = room_code                                                  # Room code for the host
            threading.Thread(target=self.broadcast_room_code, daemon=True).start()      # Start the broadcast thread in the background

        # Canvas Events
        self.canvas.bind('<B1-Motion>', self.draw)          # Bind the left mouse button motion to the draw method
        self.canvas.bind('<ButtonRelease-1>', self.reset)   # Bind the left mouse button release to the reset method
  
    def start_server(self):
        try:
            
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)     # Set the socket option to reuse the address
            self.sock.bind((self.ip, self.port))                                # Bind the socket to the host IP and port

            if self.port == 0:
                self.port = self.sock.getsockname()[1]                          # Get the port number if it was set to 0
            print(f"Server started at {self.ip}:{self.port}")

            self.peer_map[self.user_name] = (self.ip, self.port)               # Add the host to the peer map
            self.update_peers_list()                                           # Update the list of connected peers

            self.sock.listen(5)                                                     # Listen for incoming connections
            while True:
                conn, addr = self.sock.accept()                             # Accept incoming connections        
                data = conn.recv(BUFFER_SIZE)                               # Receive data from the connection
                peer_name, peer_ip, peer_port = pickle.loads(data)          # Unpack the data into peer name, IP, and port
                self.peers.append(conn)                                     # Add the connection to the list of peers
                self.peer_map[peer_name] = (peer_ip, peer_port)             # Add the peer to the peer map
                self.update_peers_list()                                    # Update the list of connected peers
                print(f"Peer connected: {peer_name} ({peer_ip}:{peer_port})")
                self.broadcast_peers()                                                          # Broadcast the updated list of peers
                threading.Thread(target=self.receive_data, args=(conn,), daemon=True).start()   # Start a thread to receive data from the peer
        except Exception as e:
            print(f"Server error: {e}")

    def broadcast_room_code(self):
        broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            try:
                data = pickle.dumps((MAP, {self.room_code: (self.ip, self.port)}))
                broadcast_sock.sendto(data, ('<broadcast>', BROADCAST_PORT))
                threading.Event().wait(5)
            except Exception as e:
                print(f"Broadcast error: {e}")

    def draw(self, event):
        if self.old_x and self.old_y:
            x, y = event.x, event.y
            self.brush_size = self.size_slider.get()
            self.canvas.create_line(self.old_x, self.old_y, x, y, width=self.brush_size, fill=self.brush_color, capstyle=tk.ROUND, smooth=tk.TRUE)
            
            # Aggregate drawing data
            if not hasattr(self, 'draw_data'):
                self.draw_data = []
            self.draw_data.append((self.old_x, self.old_y, x, y, self.brush_color, self.brush_size))
            
            # Batch send drawing data
            if len(self.draw_data) >= 10:  # Adjust the batch size as needed
                data = pickle.dumps((DRAW, self.draw_data))
                for peer in self.peers:
                    try:
                        peer.send(data)
                    except Exception as e:
                        print(f"Error sending draw data: {e}")
                self.draw_data = []  # Clear the batch after sending

        self.old_x, self.old_y = event.x, event.y

    def flush_draw_data(self):
        if hasattr(self, 'draw_data') and self.draw_data:
            data = pickle.dumps((DRAW, self.draw_data))
            for peer in self.peers:
                try:
                    peer.send(data)
                except Exception as e:
                    print(f"Error sending draw data: {e}")
            self.draw_data = []

    def reset(self, event):
        self.old_x, self.old_y = None, None

    def clear_canvas(self):
        self.canvas.delete("all")
        data = pickle.dumps((CLEAR, None))
        for peer in self.peers:
            try:
                peer.send(data)
            except Exception as e:
                print(f"Error sending clear command: {e}")

    def receive_data(self, conn):
        while True:
            try:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    break
                message_type, payload = pickle.loads(data)
                if message_type == DRAW:
                    for draw_data in payload:
                        old_x, old_y, x, y, color, size = draw_data
                        self.canvas.create_line(old_x, old_y, x, y, width=size, fill=color, capstyle=tk.ROUND, smooth=tk.TRUE)
                elif message_type == CLEAR:
                    self.canvas.delete("all")
                elif message_type == PEER:
                    new_peers = payload
                    for name, addr in new_peers.items():
                        if addr != (self.ip, self.port) and name not in self.peer_map:
                            self.peer_map[name] = addr
                            self.update_peers_list()
                            self.connect_to_peer(addr[0], addr[1])
            except Exception as e:
                print(f"Connection error: {e}")
                break
        conn.close()
        if conn in self.peers:
            self.peers.remove(conn)

    def update_peers_list(self):
        self.peers_list.delete(0, tk.END)
        for name, addr in self.peer_map.items():
            self.peers_list.insert(tk.END, f"{name}")

    def broadcast_peers(self):
        data = pickle.dumps((PEER, self.peer_map))
        for peer in self.peers:
            try:
                peer.send(data)
            except Exception as e:
                print(f"Error sending peer list: {e}")

    def choose_color(self):
        color = colorchooser.askcolor(color=self.brush_color)[1]
        if color:
            self.brush_color = color

    def choose_bg_color(self):
            color = colorchooser.askcolor(color=self.canvas['bg'])[1]
            if color:
                self.canvas.config(bg=color)

    
       

    def manual_connect(self, code, shared_room_map):
        if code not in shared_room_map:
            messagebox.showerror("Error", "Room Code not found.")
            return

        peer_ip, peer_port = shared_room_map[code]
        try:
            peer_port = int(peer_port)
            peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_sock.connect((peer_ip, peer_port))

            data = pickle.dumps((self.user_name, self.ip, self.port))
            peer_sock.send(data)

            peer_data = peer_sock.recv(BUFFER_SIZE)
            message_type, peer_list = pickle.loads(peer_data)
            if message_type == PEER:
                self.peer_map.update(peer_list)
                self.update_peers_list()

            self.peers.append(peer_sock)
            self.update_peers_list()
            print(f"Connected to peer at {peer_ip}:{peer_port}")

            self.broadcast_peers()
            threading.Thread(target=self.receive_data, args=(peer_sock,), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to peer: {e}")


    def connect_to_peer(self, peer_ip, peer_port):
        try:
            peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_sock.connect((peer_ip, peer_port))

            # Send this user's name and listening port to the peer during the handshake
            data = pickle.dumps((self.user_name, self.ip, self.port))
            peer_sock.send(data)

            self.peers.append(peer_sock)
            self.update_peers_list()
            print(f"Automatically connected to peer at {peer_ip}:{peer_port}")

            threading.Thread(target=self.receive_data, args=(peer_sock,), daemon=True).start()
        except Exception as e:
            print(f"Failed to connect to peer {peer_ip}:{peer_port}: {e}")


# Entry point for the program
if __name__ == "__main__":
    
    ip = socket.gethostbyname(socket.gethostname())                         # Get the IP address of the host
    port = 0                                                                # Set the port number to 0
    user_name = simpledialog.askstring("Name", "Enter your name:")          # Prompt the user to enter their name


    if not user_name:
        messagebox.showerror("Error", "Name is required.")
        exit()



    def main_menu():
        def create_room():
            room_code = generate_room_code()                                                            # Generate a random room code
            root.destroy()                                                                              # Close the main menu window
            whiteboard_root = tk.Tk()                                                                   # Create a new Tkinter window for the whiteboard 
            app = Whiteboard(whiteboard_root, ip, port, user_name, is_host=True, room_code=room_code)   # Initialize the whiteboard
            whiteboard_root.mainloop()                                                                  # Start the whiteboard

        def join_room():
            # Create a temporary socket to listen for room maps
            listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)                              # Create a UDP socket
            listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)                           # Set the socket option to reuse the address
            listen_sock.bind(('', BROADCAST_PORT))                                                      # Bind the socket to the broadcast port to collect room maps

            shared_room_map = {}                                                                        # Dictionary to store the room maps

            def listen_for_maps():
                # Thread to listen for broadcasted room maps
                while True:
                    try:
                        data, addr = listen_sock.recvfrom(BUFFER_SIZE)                                  
                        message_type, payload = pickle.loads(data)
                        if message_type == MAP:
                            shared_room_map.update(payload)
                    except Exception as e:
                        print(f"Error receiving map: {e}")

            threading.Thread(target=listen_for_maps, daemon=True).start()

            def prompt_for_code():
                # Prompt the user to enter the room code
                room_code = simpledialog.askstring("Room Code", "Enter the Room Code:")
                if room_code in shared_room_map:
                    # Get the peer address from the shared room map
                    peer_ip, peer_port = shared_room_map[room_code]
                    try:
                        # Close the join menu and open the whiteboard
                        join_root.destroy()

                        # Initialize the whiteboard on the main thread
                        whiteboard_root = tk.Tk()
                        app = Whiteboard(whiteboard_root, ip, port, user_name, is_host=False, room_code=room_code)
                        app.manual_connect(room_code, shared_room_map)
                        whiteboard_root.mainloop()
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to open whiteboard: {e}")
                else:
                    messagebox.showerror("Error", "Invalid Room Code.")

            # Create the GUI for joining a room
            root.destroy()
            join_root = tk.Tk()
            join_root.title("Join Room")
            tk.Button(join_root, text="Enter Room Code", command=prompt_for_code).pack(pady=20)
            join_root.mainloop()


        root = tk.Tk()                                                                 
        root.title("P2P Whiteboard")                                                   
        root.geometry("300x200")                                                        
        root.configure(bg="lightblue")                                                  

        title_label = tk.Label(root, text="P2P Whiteboard", font=("Comic Sans MS", 16, "bold"), bg="lightblue", fg="black")
        title_label.pack(pady=20)                                                       

        create_button = tk.Button(root, text="Create Room", command=create_room, bg="deepskyblue", fg="white", font=("Comic Sans MS", 12, "bold"), relief=tk.RAISED, bd=2)
        create_button.pack(pady=10)                                                     

        join_button = tk.Button(root, text="Join Room", command=join_room, bg="deepskyblue", fg="white", font=("Comic Sans MS", 12, "bold"), relief=tk.RAISED, bd=2)
        join_button.pack(pady=10)                                                     

        def on_enter_create(e):
            create_button['background'] = 'dodgerblue'
            create_button['cursor'] = 'hand2'

        def on_leave_create(e):
            create_button['background'] = 'deepskyblue'
            create_button['cursor'] = ''

        create_button.bind("<Enter>", on_enter_create)
        create_button.bind("<Leave>", on_leave_create)

        def on_enter_join(e):
            join_button['background'] = 'dodgerblue'
            join_button['cursor'] = 'hand2'

        def on_leave_join(e):
            join_button['background'] = 'deepskyblue'
            join_button['cursor'] = ''

        join_button.bind("<Enter>", on_enter_join)
        join_button.bind("<Leave>", on_leave_join)
        root.mainloop()

    main_menu()         # Start the main menu