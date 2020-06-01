from model.avenet import AVENet
from torch.utils.data import DataLoader, Dataset
from utils.util import reverseTransform
from utils.dataset import AudioSet
import os
import torch
    

def generateEmbeddingsForVideoAudio(model_name="avenet.pt", use_cuda=True, use_tags=False):
    # Get video embeddings on the test set
    dataset = AudioSet("./data/video", "./data/audio")
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
    print("Loading data.")
    # for img, aud, res, vidTags, audTags, audioSample in dataloader:
    # 	break

    model = getAVENet(use_cuda)

    # Load from before
    if os.path.exists(model_name):
        model.load_state_dict(torch.load(model_name))
        print("Loading from previous checkpoint.")

    imgList, audList, resList, vidTagList, audTagList = [], [], [], [], []
    imgEmbedList, audEmbedList = [], []
    audioSampleList = []

    model.eval()
    for i, data in enumerate(dataloader):
        # Filter the bad ones first
        if use_tags:
            img, aud, res, vidTag, audTag, audSamples = data
        else:
            img, aud, res = data

        #res = res.squeeze(1)
        idx = (res != 2).numpy().astype(bool)
        if idx.sum() == 0:
            continue

        # Find the new variables
        img = torch.Tensor(img.numpy()[idx, :, :, :])
        aud = torch.Tensor(aud.numpy()[idx, :, :, :])
        res = torch.LongTensor(res.numpy()[idx])
        
        if use_tags:
            vidTag = vidTag.numpy()[idx]
            audTag = audTag.numpy()[idx]
            audSamples = audSamples.numpy()[idx]

        #with torch.no_grad():
        img = img.clone().detach()
        aud = aud.clone().detach()
        res = res.clone().detach()

        #M = img.shape[0]
        if use_cuda:
            img = img.cuda()
            aud = aud.cuda()
            res = res.cuda()

        o, imgEmbed, audEmbed = model(img, aud)
        _, ind = o.max(1)

        
        # Grab the correct indices
        idx = ((ind == res) * (res == 0)).data.cpu().numpy().astype(bool)
        print(i)

        img, aud = reverseTransform(img, aud)

        imgList.append(img.data.cpu().numpy()[idx, :])
        audList.append(aud.data.cpu().numpy()[idx, :])
        imgEmbedList.append(imgEmbed.data.cpu().numpy()[idx, :])
        audEmbedList.append(audEmbed.data.cpu().numpy()[idx, :])
        if use_tags:
            vidTagList.append(vidTag[idx])
            audTagList.append(audTag[idx])
            audioSampleList.append(audSamples[idx])

        if i == 35:
            break
    
    if use_tags:
        torch.save([imgList, audList, imgEmbedList, audEmbedList, vidTagList, audTagList, audioSampleList], "./save/embeddings/savedEmbeddings.pt")
    else:
        torch.save([imgList, audList, imgEmbedList, audEmbedList], "./save/embeddings/savedEmbeddings.pt")
    
def getAVENet(use_cuda=True):
    model = AVENet()
    # model.fc3.weight.data[0] = -0.1
    # model.fc3.weight.data[1] =  0.1
    # model.fc3.bias.data[0] =   1.0
    # model.fc3.bias.data[1] = - 1.0
    model.fc3.weight.data[0] = -0.7090
    model.fc3.weight.data[1] =  0.7090
    model.fc3.bias.data[0] =   1.2186
    model.fc3.bias.data[1] = - 1.2186
    if use_cuda:
        model = model.cuda()

    return model


if __name__ == "__main__":
    model_path = './save/ave_model/ave_83_1000.pt'
    generateEmbeddingsForVideoAudio(model_name=model_path, use_cuda=True, use_tags=False)