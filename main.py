import webview
from agv_api import Api

api = Api()

class Bridge:
    def __init__(self):
        self.api = Api()
    
    def get_robot_info(self, ip: str):
        return api.get_robot_info(ip)
    
    def scan_network(self, subnet: str):
        return api.scan_network(subnet)
    
    def get_bins(self, ip: str, map_name: str = "default", md5: str = "", force_refresh: bool = False):
        return api.get_bins(ip, map_name, md5, force_refresh)
    
    def get_nav_status(self, ip: str, simple: bool = True):
        return api.get_nav_status(ip, simple)

    def get_task_status(self, ip: str, task_ids: list[str] = None):
        return api.get_task_status(ip, task_ids)
    
    def dispatch_task(self, ip: str, bin_name: str, action: str, source_id: str = "SELF_POSITION"):
        return api.dispatch_task(ip, bin_name, action, source_id)
    
    '''
    def get_map_md5(self, ip, map_name):
        return self.api.get_map_md5(ip, map_name)
    '''
    
    def get_current_map(self, ip):
        return self.api.get_current_map(ip)
        

if __name__ == "__main__":
    bridge = Bridge()
    window = webview.create_window("AGV 派車工具", "index.html", js_api=bridge, width=1000, height=700)
    webview.start(gui="edgechromium", debug=True)
