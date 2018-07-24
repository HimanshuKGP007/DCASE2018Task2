import torch.nn as nn
import math
import torch.utils.model_zoo as model_zoo
import torch

__all__ = ['ResNet', 'resnet18', 'resnet34', 'resnet50', 'resnet101', 'resnet152',
           'waveResnet18', 'waveResnet34', 'waveResnet50', 'waveResnet101',
           'logmelResnet18', 'logmelResnet34', 'logmelResnet50', 'logmelResnet101']


model_urls = {
    'resnet18': 'https://download.pytorch.org/models/resnet18-5c106cde.pth',
    'resnet34': 'https://download.pytorch.org/models/resnet34-333f7ec4.pth',
    'resnet50': 'https://download.pytorch.org/models/resnet50-19c8e357.pth',
    'resnet101': 'https://download.pytorch.org/models/resnet101-5d3b4d8f.pth',
    'resnet152': 'https://download.pytorch.org/models/resnet152-b121ed2d.pth',
}


def conv3x3(in_planes, out_planes, stride=1):
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride,
                               padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * 4)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class ResNet(nn.Module):

    def __init__(self, block, layers, num_classes=1000):
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = nn.AvgPool2d((7, 7), stride=(1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x

class WaveResNet(nn.Module):

    def __init__(self, block, modules):
        super(WaveResNet, self).__init__()

        self.conv1_1 = nn.Conv1d(in_channels=1, out_channels=32, kernel_size=11, stride=1, padding=5)
        self.conv1_2 = nn.Conv1d(in_channels=1, out_channels=32, kernel_size=51, stride=5, padding=25)
        self.conv1_3 = nn.Conv1d(in_channels=1, out_channels=32, kernel_size=101, stride=10, padding=50)

        self.bn1_1 = nn.BatchNorm1d(32)
        self.bn1_2 = nn.BatchNorm1d(32)
        self.bn1_3 = nn.BatchNorm1d(32)

        self.conv2_1 = nn.Conv1d(in_channels=32, out_channels=32, kernel_size=3, stride=1, padding=1)
        self.conv2_2 = nn.Conv1d(in_channels=32, out_channels=32, kernel_size=3, stride=1, padding=1)
        self.conv2_3 = nn.Conv1d(in_channels=32, out_channels=32, kernel_size=3, stride=1, padding=1)

        self.bn2_1 = nn.BatchNorm1d(32)
        self.bn2_2 = nn.BatchNorm1d(32)
        self.bn2_3 = nn.BatchNorm1d(32)
        #
        # self.conv3_1 = nn.Conv1d(in_channels=32, out_channels=32, kernel_size=3, stride=1, padding=1)
        # self.conv3_2 = nn.Conv1d(in_channels=32, out_channels=32, kernel_size=3, stride=1, padding=1)
        # self.conv3_3 = nn.Conv1d(in_channels=32, out_channels=32, kernel_size=3, stride=1, padding=1)
        #
        # self.bn3_1 = nn.BatchNorm1d(32)
        # self.bn3_2 = nn.BatchNorm1d(32)
        # self.bn3_3 = nn.BatchNorm1d(32)

        self.pool2_1 = nn.MaxPool1d(kernel_size=150, stride=150)
        self.pool2_2 = nn.MaxPool1d(kernel_size=30, stride=30)
        self.pool2_3 = nn.MaxPool1d(kernel_size=15, stride=15)

        self.conv0  = nn.Conv2d(1, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn0 = nn.BatchNorm2d(64)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.resBlocks = nn.Sequential(*modules)

        self.relu = nn.ReLU(inplace=True)
        self.avgpool = nn.AvgPool2d((3, 14), stride=(1, 1))
        self.fc = nn.Linear(512 * block.expansion, 41)
        
        for m in self.children():
           if isinstance(m, nn.Conv2d):
               n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
               m.weight.data.normal_(0, math.sqrt(2. / n))
           elif isinstance(m, nn.BatchNorm2d):
               m.weight.data.fill_(1)
               m.bias.data.zero_()



    def forward(self, x):
        x1 = self.relu(self.bn1_1(self.conv1_1(x)))
        x2 = self.relu(self.bn1_2(self.conv1_2(x)))
        x3 = self.relu(self.bn1_3(self.conv1_3(x)))

        x1 = self.relu(self.bn2_1(self.conv2_1(x1)))
        x2 = self.relu(self.bn2_2(self.conv2_2(x2)))
        x3 = self.relu(self.bn2_3(self.conv2_3(x3)))
        #
        # x1 = self.relu(self.bn3_1(self.conv3_1(x1)))
        # x2 = self.relu(self.bn3_2(self.conv3_2(x2)))
        # x3 = self.relu(self.bn3_3(self.conv3_3(x3)))

        x1 = self.pool2_1(x1)
        x2 = self.pool2_2(x2)
        x3 = self.pool2_3(x3)  # (batchSize, 32L, 441L)

        x1 = torch.unsqueeze(x1, 1)
        x2 = torch.unsqueeze(x2, 1)
        x3 = torch.unsqueeze(x3, 1)  # (batchSize, 1L, 32L, 441L)

        x = torch.cat((x1, x2, x3), dim=2) #(batchSize, 1L, 96L, 441L)
        #  x = torch.cat((x1, x2, x3), dim=1)  # (batchSize, 2L, 96L, 441L)


        x = self.conv0(x)
        x = self.bn0(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.resBlocks(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

class SWaveResNet(nn.Module):

    def __init__(self, block, modules):
        super(SWaveResNet, self).__init__()

        self.conv0  = nn.Conv2d(1, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn0 = nn.BatchNorm2d(64)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.conv1_1 = nn.Conv1d(in_channels=1, out_channels=32, kernel_size=11, stride=1, padding=5)

        self.bn1_1 = nn.BatchNorm1d(32)

        self.conv2_1 = nn.Conv1d(in_channels=32, out_channels=32, kernel_size=11, stride=1, padding=5)

        self.bn2_1 = nn.BatchNorm1d(32)

        self.pool2_1 = nn.MaxPool1d(kernel_size=150, stride=150)

        self.resBlocks = nn.Sequential(*modules)

        self.relu = nn.ReLU(inplace=True)
        self.avgpool = nn.AvgPool2d((3, 14), stride=(1, 1))
        self.fc = nn.Linear(512 * block.expansion, 50)

        for m in self.children():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()



    def forward(self, x):
        x1 = self.relu(self.bn1_1(self.conv1_1(x)))
        x2 = self.relu(self.bn1_2(self.conv1_2(x)))
        x3 = self.relu(self.bn1_3(self.conv1_3(x)))

        x1 = self.relu(self.bn2_1(self.conv2_1(x1)))
        x2 = self.relu(self.bn2_2(self.conv2_2(x2)))
        x3 = self.relu(self.bn2_3(self.conv2_3(x3)))

        x1 = self.pool2_1(x1)
        x2 = self.pool2_2(x2)
        x3 = self.pool2_3(x3)  # (batchSize, 32L, 441L)

        x1 = torch.unsqueeze(x1, 1)
        x2 = torch.unsqueeze(x2, 1)
        x3 = torch.unsqueeze(x3, 1)  # (batchSize, 1L, 32L, 441L)

        x = torch.cat((x1, x2, x3), dim=2) #(batchSize, 1L, 96L, 441L)
        # x = torch.cat((x, x), dim=1)  # (batchSize, 2L, 96L, 441L)

        x = self.conv0(x)
        x = self.bn0(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.resBlocks(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x


class LogmelResNet(nn.Module):

    def __init__(self, block, modules, num_classes=50):
        self.inplanes = 64
        super(LogmelResNet, self).__init__()


        self.conv0  = nn.Conv2d(1, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn0 = nn.BatchNorm2d(64)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.relu = nn.ReLU(inplace=True)

        self.resBlocks = nn.Sequential(*modules)

        self.avgpool = nn.AvgPool2d((3, 14), stride=(1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.children():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def forward(self, x):
        x = self.conv0(x)
        x = self.bn0(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.resBlocks(x)
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

def resnet18(pretrained=False, **kwargs):
    """Constructs a ResNet-18 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(BasicBlock, [2, 2, 2, 2], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet18']))
    return model


def resnet34(pretrained=False, **kwargs):
    """Constructs a ResNet-34 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(BasicBlock, [3, 4, 6, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet34']))
    return model


def resnet50(pretrained=False, **kwargs):
    """Constructs a ResNet-50 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 4, 6, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet50']))
    return model


def resnet101(pretrained=False, **kwargs):
    """Constructs a ResNet-101 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 4, 23, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet101']))
    return model


def resnet152(pretrained=False, **kwargs):
    """Constructs a ResNet-152 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 8, 36, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['resnet152']))
    return model

def waveResnet18(pretrained=False, **kwargs):
    """Constructs a waveResNet-18 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """

    if pretrained == True:
        resnet = resnet18(pretrained)
    else:
        resnet = resnet18()

    modules = list(resnet.children())[4:8]
    model = WaveResNet(BasicBlock, modules)
    return model

def waveResnet34(pretrained=False, **kwargs):
    """Constructs a waveResNet-34 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """

    if pretrained == True:
        resnet = resnet34(pretrained)
    else:
        resnet = resnet34()

    modules = list(resnet.children())[4:8]
    model = WaveResNet(BasicBlock, modules)
    return model

def waveResnet50(pretrained=False, **kwargs):
    """Constructs a waveResNet-18 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """

    if pretrained == True:
        resnet = resnet50(pretrained)
    else:
        resnet = resnet50()

    # layer1,2,3,4
    modules = list(resnet.children())[4:8]
    model = WaveResNet(Bottleneck, modules)
    return model

def waveResnet101(pretrained=False, **kwargs):
    """Constructs a waveResNet-18 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """

    if pretrained == True:
        resnet = resnet101(pretrained)
    else:
        resnet = resnet101()

    # layer1,2,3,4
    modules = list(resnet.children())[4:8]
    model = WaveResNet(Bottleneck, modules)
    return model

def logmelResnet18(pretrained=False, **kwargs):
    """Constructs a LogmelResNet-18 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """

    if pretrained == True:
        resnet = resnet18(pretrained)
    else:
        resnet = resnet18()

    modules = list(resnet.children())[4:8]
    model = LogmelResNet(BasicBlock, modules)
    return model

def logmelResnet34(pretrained=False, **kwargs):
    """Constructs a LogmelResNet-18 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """

    if pretrained == True:
        resnet = resnet34(pretrained)
    else:
        resnet = resnet34()

    modules = list(resnet.children())[4:8]
    model = LogmelResNet(BasicBlock, modules)
    return model

def logmelResnet50(pretrained=False, **kwargs):
    """Constructs a LogmelResNet-50 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """

    if pretrained == True:
        resnet = resnet50(pretrained)
    else:
        resnet = resnet50()

    modules = list(resnet.children())[4:8]
    model = LogmelResNet(Bottleneck, modules)
    return model


def logmelResnet101(pretrained=False, **kwargs):
    """Constructs a LogmelResNet-50 model.

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """

    if pretrained == True:
        resnet = resnet101(pretrained)
    else:
        resnet = resnet101()

    modules = list(resnet.children())[4:8]
    model = LogmelResNet(Bottleneck, modules)
    return model


if __name__ == '__main__':
    model = waveResnet18()
