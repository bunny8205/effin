from cryptography.fernet import Fernet
FERNET_KEY = "cVjDVe62vqCkmqPwvDZcTxVPuedyYt4pVQnXsnRf6KA="
fernet = Fernet(FERNET_KEY.encode())

token = b"gAAAAABpMqJckXnkGv7z-Sk6qwZx7ZQvgvwsFI22uaY1JLB0rtJf4AW-Ye_EaEczynqhVPGBH7S4l9gsrFY1uLhSyk3dBz4KaSb730fQaOkV5-0t9ZaY6wrT1HgPV_PJPovPEl8pbZhJG3gNWmO2EUyFveAF9BF4_SaCw9CPgmgowSpb9WfCFnS7UmP8hibFMR2_XDKwNpTvdYvgukNz5mNY7_HY3o8Lvg=="   # copy 1 full line here
print(fernet.decrypt(token))
