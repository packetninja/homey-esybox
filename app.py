"""
DAB Pumps / Esybox Homey app.

Cloud-based integration with DAB Pumps water pressure pumps (Esybox, Esybox Mini, etc.).
Authentication and data retrieval is done via the DAB DConnect / DAB Live cloud.
"""

from homey.app import App


class DabPumpsApp(App):
    async def on_init(self) -> None:
        self.log("DAB Pumps / Esybox app started")


homey_export = DabPumpsApp
