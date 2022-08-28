# StackedBot

##Explanation of Origin

When StackedInvest.com had their bot program up, this was the code that sent the signals.


###How it worked

1. Receive cryptocurrency data from Binace via Websockets.

2. Parse messages using classes/algoritms.

3. When parameters hit for trade open, send messages to StackedInvest.

4. Moniter Websocket data for closing signals.

5. Once trade closed, go back to step 1. 

### Trade Data

Available in my other repositories. Actual strategy has been removed. 

