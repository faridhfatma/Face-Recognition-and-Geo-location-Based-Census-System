import requests

def get_public_ip():
    response = requests.get('https://api.ipify.org?format=json')
    ip_data = response.json()
    return ip_data['ip']


    
def get_geolocation():
    api_key = '78884ebd952828'
    response = requests.get('https://api.ipify.org?format=json')
    ip_data = response.json()
    public_ip = ip_data['ip']
    url = f"https://ipinfo.io/{public_ip}/geo"
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return None
    except requests.RequestException as e:
        print(f"Error getting geolocation data: {e}")
        return None