import requests

def fetch_medals_data(api_url, country=None):
	try:
		if country != None:
			api_url = f'{api_url}?country={country}'
		response = requests.get(api_url)
		response.raise_for_status()  # Ensure we notice bad requests
		return response.json()

	except requests.RequestException as e:
		# Handle any errors
		print(f"Error fetiching data from API: {e}")
		return None